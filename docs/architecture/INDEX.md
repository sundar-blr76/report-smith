# ReportSmith Architecture Documentation Index

Welcome to the ReportSmith architecture documentation! This index helps you find the right documentation for your needs.

## 🚀 Quick Start

**New to ReportSmith?** Start here:
1. [Context Diagram](c4-context.puml) - What is ReportSmith? (2 min)
2. [Workflow Diagram](workflow-diagram.puml) - How does it work? (10 min)
3. [Quick Reference](QUICK_REFERENCE.md) - Key concepts and components (15 min)

**Want to contribute?** Read these:
1. [Component Diagram](c4-component.puml) - Code structure
2. [Data Flow Diagram](data-flow-diagram.puml) - Component interactions
3. [C4 Architecture Guide](C4_ARCHITECTURE.md) - Complete documentation

## 📚 Documentation by Role

### For Business Stakeholders
- **[Context Diagram](c4-context.puml)** - System overview and business context
- **[Workflow Diagram](workflow-diagram.puml)** - How queries are processed
- **[Quick Reference](QUICK_REFERENCE.md)** - Executive summary (first section)

### For Architects
- **[Container Diagram](c4-container.puml)** - Technology architecture
- **[Component Diagram](c4-component.puml)** - Internal design patterns
- **[C4 Architecture Guide](C4_ARCHITECTURE.md)** - Complete architecture documentation
- **[Quick Reference](QUICK_REFERENCE.md)** - Design principles and patterns

### For Developers
- **[Component Diagram](c4-component.puml)** - Code organization and structure
- **[Workflow Diagram](workflow-diagram.puml)** - Processing pipeline
- **[Data Flow Diagram](data-flow-diagram.puml)** - Component interactions
- **[C4 Architecture Guide](C4_ARCHITECTURE.md)** - Implementation details
- **[Quick Reference](QUICK_REFERENCE.md)** - Technology stack and extending the system

### For DevOps/SRE
- **[Container Diagram](c4-container.puml)** - Deployment architecture
- **[Context Diagram](c4-context.puml)** - External dependencies
- **[Quick Reference](QUICK_REFERENCE.md)** - Performance metrics and optimization

## 📖 Documentation by Purpose

### Understanding the System
| Purpose | Document | Est. Time |
|---------|----------|-----------|
| What does it do? | [Context Diagram](c4-context.puml) | 2 min |
| How does it work? | [Workflow Diagram](workflow-diagram.puml) | 10 min |
| What's the tech stack? | [Container Diagram](c4-container.puml) | 5 min |
| Quick overview | [Quick Reference](QUICK_REFERENCE.md) | 15 min |
| Complete details | [C4 Architecture Guide](C4_ARCHITECTURE.md) | 45 min |

### Working with Diagrams
| Purpose | Document |
|---------|----------|
| How to view diagrams | [Viewing Guide](VIEWING_GUIDE.md) |
| Which diagram to use | [Diagram Selection Guide](DIAGRAM_SELECTION_GUIDE.md) |
| Diagram source files | `*.puml` files |

### Development & Implementation
| Purpose | Document |
|---------|----------|
| Code structure | [Component Diagram](c4-component.puml) |
| Component interactions | [Data Flow Diagram](data-flow-diagram.puml) |
| Query processing flow | [Workflow Diagram](workflow-diagram.puml) |
| Extension points | [C4 Architecture Guide](C4_ARCHITECTURE.md) |
| Design principles | [Quick Reference](QUICK_REFERENCE.md) |

## 🎯 Common Tasks

### I want to...

**Understand the architecture**
→ Start with [Quick Reference](QUICK_REFERENCE.md), then [C4 Architecture Guide](C4_ARCHITECTURE.md)

**Onboard a new team member**
→ Use [Diagram Selection Guide](DIAGRAM_SELECTION_GUIDE.md) - "Scenario 1: New Team Member Onboarding"

**Add a new feature**
→ Review [Component Diagram](c4-component.puml) and [Workflow Diagram](workflow-diagram.puml)

**Debug an issue**
→ Use [Data Flow Diagram](data-flow-diagram.puml) to trace interactions

**Optimize performance**
→ See [Workflow Diagram](workflow-diagram.puml) and [Quick Reference](QUICK_REFERENCE.md) - "Performance Metrics"

**Present to stakeholders**
→ Use [Diagram Selection Guide](DIAGRAM_SELECTION_GUIDE.md) - "For Presentations"

**Set up deployment**
→ Review [Container Diagram](c4-container.puml)

**Understand security boundaries**
→ Check [Context Diagram](c4-context.puml) and [Container Diagram](c4-container.puml)

## 📁 File Organization

```
docs/architecture/
├── README.md                          # This directory overview
├── INDEX.md                           # This file - navigation guide
│
├── C4_ARCHITECTURE.md                 # Complete architecture documentation
├── QUICK_REFERENCE.md                 # Quick reference guide
├── VIEWING_GUIDE.md                   # How to view PlantUML diagrams
├── DIAGRAM_SELECTION_GUIDE.md         # Choosing the right diagram
│
├── c4-context.puml                    # C4 Level 1: System Context
├── c4-container.puml                  # C4 Level 2: Containers
├── c4-component.puml                  # C4 Level 3: Components
│
├── workflow-diagram.puml              # 8-stage query workflow
└── data-flow-diagram.puml             # Sequence/interaction diagram
```

## 🔗 Related Documentation

### In This Repository
- [Main README](../../README.md) - Project overview and getting started
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Original architecture documentation
- [HLD.md](../HLD.md) - High-level design document
- [LLD.md](../LLD.md) - Low-level design document
- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) - Database schema details
- [SETUP.md](../../SETUP.md) - Installation and setup guide

### External Resources
- [C4 Model](https://c4model.com/) - C4 model documentation
- [PlantUML](https://plantuml.com/) - PlantUML documentation
- [LangGraph](https://langchain-ai.github.io/langgraph/) - LangGraph framework

## 🛠️ Tools and Setup

### Viewing Diagrams
See [VIEWING_GUIDE.md](VIEWING_GUIDE.md) for detailed instructions.

**Quick options**:
- **Online**: [PlantUML Online Editor](http://www.plantuml.com/plantuml/uml/)
- **VS Code**: Install "PlantUML" extension
- **Command line**: `plantuml *.puml`

### Generating Images

```bash
# Install PlantUML
sudo apt-get install plantuml  # Linux
brew install plantuml          # macOS

# Generate all diagrams as PNG
cd docs/architecture
plantuml *.puml

# Generate specific diagram as SVG
plantuml -tsvg c4-context.puml
```

## 📊 Diagram Overview

| Diagram | Type | Complexity | Best For |
|---------|------|------------|----------|
| Context | C4-L1 | ⭐ Low | All audiences |
| Container | C4-L2 | ⭐⭐ Medium | Technical audiences |
| Component | C4-L3 | ⭐⭐⭐ High | Developers |
| Workflow | Process | ⭐⭐ Medium | Understanding flow |
| Data Flow | Sequence | ⭐⭐⭐⭐ Very High | Debugging |

## 💡 Tips

1. **Start simple**: Don't try to understand everything at once
2. **Use the right diagram**: See [DIAGRAM_SELECTION_GUIDE.md](DIAGRAM_SELECTION_GUIDE.md)
3. **Follow the learning path**: Context → Workflow → Container → Component → Data Flow
4. **Ask questions**: Open an issue if something is unclear
5. **Keep updated**: Update diagrams when making architectural changes

## 🆘 Getting Help

**Can't view diagrams?**
→ See [VIEWING_GUIDE.md](VIEWING_GUIDE.md) - "Troubleshooting" section

**Don't know which diagram to use?**
→ See [DIAGRAM_SELECTION_GUIDE.md](DIAGRAM_SELECTION_GUIDE.md)

**Want more detail?**
→ Read [C4_ARCHITECTURE.md](C4_ARCHITECTURE.md)

**Need a quick overview?**
→ See [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

**Have questions?**
→ Open an issue on GitHub or contact the development team

---

**Last Updated**: 2025-12-15  
**Maintained By**: ReportSmith Development Team

**Feedback**: We'd love to hear how we can improve this documentation. Please open an issue with suggestions!
