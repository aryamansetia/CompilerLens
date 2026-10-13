/**
 * Every call to the backend goes through this file.
 *
 * During development Vite forwards /api to http://127.0.0.1:8000 (see
 * vite.config.js), so no server address appears anywhere in the components.
 */

const BASE_URL = "/api";

/** Turns a failed response into a readable message instead of "[object Object]". */
async function describeFailure(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
    }
  } catch {
    // response had no JSON body
  }
  return `The server replied with status ${response.status}.`;
}

async function getJson(path) {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) throw new Error(await describeFailure(response));
  return response.json();
}

/** Runs the implemented compiler phases on one program. */
export async function analyzeSource(sourceCode, language) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_code: sourceCode, language }),
    });
  } catch {
    throw new Error(
      "Cannot reach the CompilerLens backend. Start it with: uvicorn main:app --reload"
    );
  }
  if (!response.ok) throw new Error(await describeFailure(response));
  return response.json();
}

/** Runs a program in CompilerLens' bounded educational interpreter. */
export async function runProgram(sourceCode, language, stdin = "") {
  let response;
  try {
    response = await fetch(`${BASE_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_code: sourceCode, language, stdin }),
    });
  } catch {
    throw new Error("Cannot reach the CompilerLens backend. Start it with: uvicorn main:app --reload");
  }
  if (!response.ok) throw new Error(await describeFailure(response));
  return response.json();
}

export const fetchExamples = () => getJson("/examples");
export const fetchLanguages = () => getJson("/languages");
export const fetchPipeline = () => getJson("/pipeline");
