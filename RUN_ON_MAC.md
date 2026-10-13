# Run CompilerLens on macOS with VS Code

This guide is for the six-phase educational CompilerLens implementation. You do not need to install a real C, C++, or Java compiler: CompilerLens analyses the supported educational grammar itself.

## 1. Extract and open the folder

1. Extract `CompilerLens_Full_Project.zip`.
2. Open VS Code.
3. Choose **File → Open Folder…** and select the extracted `CompilerLens` folder (the folder containing `README.md`, `backend`, and `frontend`).
4. Choose **Terminal → New Terminal**.

Do not open just `backend` or just `frontend` as the project root.

## 2. Start the backend

In the first VS Code terminal, run these commands one at a time:

```bash
cd backend
python3 --version
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --reload
```

Leave this terminal running. The server should report that it is listening on `127.0.0.1:8000`.

Open **http://127.0.0.1:8000** for the built-in interface. This interface is served by FastAPI and does not require Node.js, so it is the quickest fallback for a review demo.

Useful backend URLs:

- **http://127.0.0.1:8000** — built-in CompilerLens interface
- **http://127.0.0.1:8000/docs** — interactive API documentation
- **http://127.0.0.1:8000/api/health** — health check

## 3. (Recommended) Start the React frontend

Keep the backend terminal running. Open a second VS Code terminal using **Terminal → New Terminal**. From the project root, run:

```bash
cd frontend
npm install
npm run dev
```

Open the address printed by Vite, normally **http://localhost:5173**. Vite forwards `/api` requests to the backend on port 8000, so both terminals must remain running.

If the React development server has a dependency error, return to `frontend` and run:

```bash
rm -rf node_modules
npm install
npm run dev
```

The built-in page at port 8000 remains available as a fallback as long as the backend is running.

## 4. Run the test suite

Open another terminal, then run:

```bash
cd backend
source venv/bin/activate
python -m tests.test_compiler
```

Expected final line: `38/38 tests passed.`

## 5. Best program for the review

Paste this source into the editor and click **Compile / Analyze**:

```c
int a = 10;
int b = 20;
int c = a + b * 2;
```

Open **Symbol table** to show `a`, `b`, and `c` with their types and initialisation status. Open **Intermediate code** to show:

```text
a = 10
b = 20
t1 = b * 2
t2 = a + t1
c = t2
```

This result demonstrates that multiplication is evaluated before addition, and that the expression is lowered into simple three-address instructions.

For a quick boolean type-checking demo, choose C++ and try `bool ready = true;` followed by `bool finished = false;`. Choose Java and try the same with `boolean`. The symbol table should show the declared types, and the Intermediate Code tab should show assignments for `true` and `false`. Boolean literals are supported in the current C++/Java subset; they are not treated as boolean literals in C.

To demonstrate semantic error handling, try:

```c
int total = price + 5;
```

The **Errors** tab should report that `price` is used before it is declared, and the Intermediate Code tab should be empty because code generation is blocked when semantic errors are present.

## 6. Demonstrate optimization and code generation

Use this program to make the optimizer show a visible transformation:

```c
int a = 10;
int c = a + 2 * 3;
```

The original TAC should contain `t1 = 2 * 3`. The Optimization tab should fold this
into `6`, propagate the temporary value, and remove the now-unused temporary.
Then open the Code Generation tab to see the resulting instructions for the
CompilerLens educational register machine. This is pseudo-assembly for explaining
the compiler pipeline, not native machine code or a directly executable program.

## 7. Stop the servers

When you are finished, click a terminal running the server and press **Control + C**. Do this in each terminal.
