import { useCallback, useEffect, useState } from "react";

import { analyzeSource, fetchExamples, fetchLanguages, fetchPipeline, runProgram as executeProgram } from "./api.js";
import AstTree from "./components/AstTree.jsx";
import CodeEditor from "./components/CodeEditor.jsx";
import ErrorList from "./components/ErrorList.jsx";
import ExamplePicker from "./components/ExamplePicker.jsx";
import IntermediateCode from "./components/IntermediateCode.jsx";
import OptimizationResult from "./components/OptimizationResult.jsx";
import TargetCode from "./components/TargetCode.jsx";
import PipelineStrip from "./components/PipelineStrip.jsx";
import RoadmapPanel from "./components/RoadmapPanel.jsx";
import StatBar from "./components/StatBar.jsx";
import SymbolTable from "./components/SymbolTable.jsx";
import Tabs from "./components/Tabs.jsx";
import TokenTable from "./components/TokenTable.jsx";
import ExecutionConsole from "./components/ExecutionConsole.jsx";

const DEFAULT_PROGRAM = "int a = 10;\nint b = 20;\nint c = a + 2 * 3;\n";

const FALLBACK_LANGUAGES = [
  { id: "c", label: "C" },
  { id: "cpp", label: "C++" },
  { id: "java", label: "Java" },
];

export default function App() {
  const [sourceCode, setSourceCode] = useState(DEFAULT_PROGRAM);
  const [language, setLanguage] = useState("c");

  const [result, setResult] = useState(null);
  const [pipeline, setPipeline] = useState([]);
  const [examples, setExamples] = useState([]);
  const [languages, setLanguages] = useState(FALLBACK_LANGUAGES);

  const [busy, setBusy] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [activeTab, setActiveTab] = useState("tokens");
  const [programInput, setProgramInput] = useState("");
  const [runResult, setRunResult] = useState(null);
  const [runError, setRunError] = useState("");
  const [running, setRunning] = useState(false);

  // Load the static data once, so the pipeline strip is visible before the
  // first analysis runs.
  useEffect(() => {
    // The first analysis may finish before this request does. Keep whichever
    // pipeline already carries results rather than overwriting it with the
    // blank version.
    fetchPipeline()
      .then((phases) => setPipeline((current) => (current.length ? current : phases)))
      .catch(() => {});
    fetchExamples().then(setExamples).catch(() => {});
    fetchLanguages()
      .then((items) => setLanguages(items.map(({ id, label }) => ({ id, label }))))
      .catch(() => {});
  }, []);

  const runAnalysis = useCallback(async () => {
    setBusy(true);
    setConnectionError("");
    try {
      const response = await analyzeSource(sourceCode, language);
      setResult(response);
      setPipeline(response.phases);
      // Semantic diagnostics deserve immediate attention just like lexer/parser errors.
      setActiveTab(response.success ? "tokens" : "errors");
    } catch (error) {
      setConnectionError(error.message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  }, [sourceCode, language]);

  const runProgram = useCallback(async () => {
    setRunning(true);
    setRunError("");
    try {
      const response = await executeProgram(sourceCode, language, programInput);
      setRunResult(response);
      if (!response.success) setRunError(response.stderr);
    } catch (error) {
      setRunResult(null);
      setRunError(error.message);
    } finally {
      setRunning(false);
    }
  }, [sourceCode, language, programInput]);

  // Analyse the default program on first load so the screen is never empty.
  useEffect(() => {
    runAnalysis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function loadExample(example) {
    setSourceCode(example.source_code);
    setLanguage(example.language);
  }

  const lexicalErrors = result?.lexical_errors ?? [];
  const syntaxErrors = result?.syntax_errors ?? [];
  const semanticErrors = result?.semantic_errors ?? [];
  const tokens = result?.tokens ?? [];
  const symbolTable = result?.symbol_table ?? [];
  const intermediateCode = result?.intermediate_code ?? [];
  const totalErrors = lexicalErrors.length + syntaxErrors.length + semanticErrors.length;

  const tabs = [
    { id: "tokens", label: "Tokens", count: tokens.length },
    { id: "ast", label: "Syntax tree", count: result?.statistics?.ast_node_count ?? 0 },
    { id: "symbols", label: "Symbol table", count: symbolTable.length },
    { id: "intermediate", label: "Intermediate code", count: intermediateCode.length },
    { id: "optimization", label: "Optimization", count: result?.optimized_code?.length ?? 0 },
    { id: "codegen", label: "Code generation", count: result?.target_instruction_count ?? 0 },
    { id: "errors", label: "Errors", count: totalErrors, tone: "alert" },
    { id: "roadmap", label: "Pipeline status" },
  ];

  return (
    <div className="app">
      <header className="masthead">
        <div className="brand">
          <h1>CompilerLens</h1>
          <p>Watch a program move through compiler phases.</p>
        </div>
        <p className="milestone">
            Six compiler phases cover scalar declarations, functions, conditions, and loops in the supported subset.
        </p>
      </header>

      <PipelineStrip phases={pipeline} />

      {connectionError && (
        <div className="banner" role="alert">
          <strong>Backend unavailable.</strong> {connectionError}
        </div>
      )}

      <main className="workspace">
        <div className="column column--input">
          <CodeEditor
            value={sourceCode}
            onChange={setSourceCode}
            language={language}
            onLanguageChange={setLanguage}
            languages={languages}
            onAnalyze={runAnalysis}
            busy={busy}
          />
          <ExamplePicker examples={examples} onPick={loadExample} />
          <ExecutionConsole
            input={programInput}
            onInputChange={setProgramInput}
            onRun={runProgram}
            running={running}
            result={runResult}
            error={runError}
          />
        </div>

        <div className="column column--output">
          <section className="panel results-panel">
            <StatBar statistics={result?.statistics} success={result?.success} />
            <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />

            <div className="tab-body">
              {activeTab === "tokens" && <TokenTable tokens={tokens} />}
              {activeTab === "ast" && <AstTree ast={result?.ast} astText={result?.ast_text} />}
              {activeTab === "symbols" && <SymbolTable symbols={symbolTable} />}
              {activeTab === "intermediate" && (
                <IntermediateCode
                  instructions={intermediateCode}
                  codeText={result?.intermediate_code_text ?? ""}
                  temporaryCount={result?.temporary_count ?? 0}
                />
              )}
              {activeTab === "optimization" && (
                <OptimizationResult
                  originalText={result?.intermediate_code_text ?? ""}
                  optimizedInstructions={result?.optimized_code ?? []}
                  optimizedText={result?.optimized_code_text ?? ""}
                  notes={result?.optimization_notes ?? []}
                />
              )}
              {activeTab === "codegen" && (
                <TargetCode
                  lines={result?.target_code ?? []}
                  text={result?.target_code_text ?? ""}
                  targetName={result?.target_name ?? ""}
                  instructionCount={result?.target_instruction_count ?? 0}
                  note={result?.target_code_note ?? ""}
                />
              )}
              {activeTab === "errors" && (
                <ErrorList
                  lexicalErrors={lexicalErrors}
                  syntaxErrors={syntaxErrors}
                  semanticErrors={semanticErrors}
                />
              )}
              {activeTab === "roadmap" && <RoadmapPanel phases={pipeline} />}
            </div>
          </section>
        </div>
      </main>

      <footer className="colophon">
        Compiler Design Lab project · FastAPI backend, React frontend · six educational phases implemented
      </footer>
    </div>
  );
}
