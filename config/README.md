# Configuration Directory

## 📁 Structure

```
config/
├── applications/      # Application configs (one per external system)
│   ├── README.md
│   └── fund_accounting.yaml
└── logging.yaml      # Logging configuration
```

## 🗂️ Applications

Application configurations in `applications/` directory.

Each YAML file describes:
- Database connections (by region)
- Table schemas
- Business context
- Relationships

See [applications/README.md](applications/README.md) for details.

## 🔐 Security

- **Passwords/API keys**: Store in environment variables (NOT in YAML)
- **Database credentials**: Use `~/.bashrc` exports
- **Never commit**: Secrets to git

Example `.bashrc`:
```bash
export REPORTSMITH_DB_PASSWORD="your_password"
export YOUR_APP_DB_PASSWORD="your_password"
```
