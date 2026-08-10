Quick setup notes

1) Install light Python deps now (useful for running API/tests without heavy ML stack):

```powershell
cd sonara-backend
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-light.txt
```

2) Schedule nightly install (heavy deps) using `install-nightly.ps1` at 02:00 if desired.

3) Frontend setup (in project root `sonara-vocal-remover`):

```powershell
cd ..\sonara-vocal-remover
npm install
npm run dev
```
