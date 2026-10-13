# Start Here — CompilerLens

This folder is the complete CompilerLens source project. It includes the React frontend, FastAPI backend, built-in fallback interface, example programs, and tests. It intentionally does not include virtual environments or `node_modules`; those are created for the operating system where the project is run.

## Quickest way to open the project

1. Extract the ZIP file.
2. In VS Code, choose **File → Open Folder…** and choose this `CompilerLens` folder (the one containing `README.md`, `backend`, and `frontend`).
3. Choose **Terminal → New Terminal**.
4. Run the backend commands below one at a time.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --reload
```

5. Keep that terminal open and visit **http://127.0.0.1:8000**. This built-in interface is the quickest path and does not need Node.js.

## React frontend (recommended when ready)

Open a second terminal from the project root and run:

```bash
cd frontend
npm install
npm run dev
```

Open the localhost URL Vite prints (normally **http://localhost:5173**). Keep both terminals open.

## Verify the project

Open a third terminal and run:

```bash
cd backend
source venv/bin/activate
python -m tests.test_compiler
```

Expected result: **38/38 tests passed**.

## Review-demo order

1. Run `int a = 10; int b = 20; int c = a + b * 2;` and show Tokens, Syntax Tree, Symbol Table and Intermediate Code.
2. Run `int total = price + 5;` to show an undeclared-variable semantic error.
3. Run `int score = 10; int score = 20;` to show duplicate declaration detection.
4. Choose C++ and run `bool ready = true;` to demonstrate boolean type checking.
5. Show the Optimization tab using `int a = 10; int c = a + 2 * 3;`, then show the Code Generation tab and explain that it contains educational pseudo-assembly, not a native executable.

For fuller details, see `README.md`, `RUN_ON_MAC.md`, and `REVIEW_DEMO.md`.
