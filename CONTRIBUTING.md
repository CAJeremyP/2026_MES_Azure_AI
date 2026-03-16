# Contributing

This project is a training demo for the QA Azure AI End-to-End Solution Programme. Contributions that improve the demo experience are welcome.

## Development Setup

```bash
git clone https://github.com/YOUR_ORG/azure-ai-demo.git
cd azure-ai-demo
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt
cp .env.example .env
# Fill in .env values (requires Azure resources — see README)
```

## Branch Strategy

- `main` — stable, always deployable
- `develop` — integration branch for features
- `feature/your-feature` — individual work

## Pull Request Checklist

- [ ] Code runs without errors against a real Azure deployment
- [ ] No secrets or `.env` contents in the diff
- [ ] Docstrings updated for any changed functions
- [ ] Facilitator guides updated if demo flow changes
- [ ] Bicep changes validated with `az bicep build --file infra/main.bicep`

## Code Style

- Python: PEP 8, max line length 120
- Use `f-strings`, not `.format()` or `%`
- Type hints on all public function signatures
- All Azure calls wrapped in try/except with a helpful error message

## Adding New Azure Services

1. Add the resource to `infra/main.bicep`
2. Add the output and key retrieval to `scripts/deploy.sh`
3. Create a new module in `app/` following the pattern of `vision.py`
4. Call the module from `app/main.py` and add results to the `results` dict
5. Add a section to `app/report.py` to display the new results
6. Document in `docs/` and update `docs/cost-estimate.md`

## Reporting Issues

Open a GitHub Issue with:
- Python version (`python --version`)
- Azure CLI version (`az --version`)
- Region deployed to
- Full error traceback
- Output of `az group show --name rg-ai-demo`
