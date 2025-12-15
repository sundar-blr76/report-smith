# How to View and Use the Architecture Diagrams

This guide explains how to view and work with the PlantUML architecture diagrams.

## 📋 Quick View Options

### Option 1: Online PlantUML Editor (Easiest)

1. **Visit**: [http://www.plantuml.com/plantuml/uml/](http://www.plantuml.com/plantuml/uml/)
2. **Open any `.puml` file** from this directory
3. **Copy the entire contents**
4. **Paste into the editor**
5. **View the rendered diagram**

**Files to try**:
- `c4-context.puml` - Start here for system overview
- `workflow-diagram.puml` - See the query processing flow
- `data-flow-diagram.puml` - Understand component interactions

### Option 2: VS Code (Best for Development)

1. **Install Extension**:
   - Open VS Code
   - Search for "PlantUML" by jebbs
   - Click Install

2. **View Diagrams**:
   - Open any `.puml` file
   - Press `Alt+D` (Windows/Linux) or `Option+D` (Mac)
   - Diagram appears in preview pane

3. **Export Images**:
   - Right-click in the preview
   - Select "Export Current Diagram"
   - Choose format (PNG, SVG, etc.)

### Option 3: IntelliJ IDEA / PyCharm

1. **Enable Plugin**:
   - Go to Settings → Plugins
   - Search for "PlantUML integration"
   - Enable the plugin

2. **View Diagrams**:
   - Open any `.puml` file
   - Preview pane shows diagram automatically

### Option 4: Command Line

```bash
# Install PlantUML (requires Java)
# On Ubuntu/Debian
sudo apt-get install plantuml

# On macOS
brew install plantuml

# Generate PNG images
cd docs/architecture
plantuml *.puml

# This creates PNG files for all diagrams
# Example: c4-context.png, c4-container.png, etc.
```

### Option 5: Online PlantText

1. **Visit**: [https://www.planttext.com/](https://www.planttext.com/)
2. **Paste diagram code**
3. **Click "Refresh"**
4. **Download or share**

## 📊 Diagram Overview

### C4 Model Diagrams (Start Here)

#### 1. Context Diagram (`c4-context.puml`)
**Purpose**: Big picture - who uses the system and what external systems it depends on

**What you'll see**:
- Users: Business users and developers
- ReportSmith system boundary
- External systems: OpenAI, Gemini, databases
- Key relationships and interactions

**When to use**: Understanding system boundaries and stakeholders

#### 2. Container Diagram (`c4-container.puml`)
**Purpose**: High-level technology architecture

**What you'll see**:
- Streamlit UI (Port 8501)
- FastAPI Server (Port 8000)
- LangGraph Orchestrator
- Query Processing modules
- Schema Intelligence components
- ChromaDB vector store
- Configuration files

**When to use**: Understanding technology choices and deployment

#### 3. Component Diagram (`c4-component.puml`)
**Purpose**: Detailed internal structure

**What you'll see**:
- 8 agent nodes in the workflow
- Intent analyzers (hybrid, LLM, semantic)
- SQL builders (SELECT, JOIN, WHERE, modifiers)
- Embedding manager and knowledge graph
- Utilities (logger, LLM tracker, cache manager)
- All component interactions

**When to use**: Deep dive into implementation details

### Supplementary Diagrams

#### 4. Workflow Diagram (`workflow-diagram.puml`)
**Purpose**: Step-by-step query processing flow

**What you'll see**:
- 8 stages of the pipeline
- Data transformations at each stage
- Example: "Show AUM for equity funds"
- Component responsibilities
- Technology used at each stage

**When to use**: Understanding the query execution flow

#### 5. Data Flow Diagram (`data-flow-diagram.puml`)
**Purpose**: Sequence of interactions between components

**What you'll see**:
- Component-to-component communication
- API calls and responses
- Database queries
- LLM interactions
- Timing and sequencing

**When to use**: Debugging or optimizing the system

## 🎯 Recommended Learning Path

### For New Team Members
1. **Start**: Context diagram (big picture)
2. **Next**: Workflow diagram (how it works)
3. **Then**: Container diagram (technology stack)
4. **Finally**: Component diagram (implementation details)

### For Developers
1. **Start**: Component diagram (code structure)
2. **Next**: Data flow diagram (interactions)
3. **Then**: Workflow diagram (processing logic)
4. **Reference**: Context & container diagrams as needed

### For Architects
1. **Start**: Container diagram (architecture)
2. **Next**: Component diagram (design patterns)
3. **Then**: Context diagram (system boundaries)
4. **Reference**: Workflow & data flow for optimization

### For Stakeholders
1. **Start**: Context diagram (what does it do?)
2. **Next**: Workflow diagram (how does it work?)
3. **Optional**: Container diagram (what technology?)

## 🛠️ Working with the Diagrams

### Modifying Diagrams

1. **Open the `.puml` file** in a text editor
2. **Make changes** to the PlantUML code
3. **Preview** using one of the viewing options above
4. **Iterate** until satisfied
5. **Commit** changes to version control

### Adding New Diagrams

```plantuml
@startuml MyDiagram
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

title My New Diagram

' Add your content here

@enduml
```

### PlantUML Syntax Resources

- **Official Documentation**: [https://plantuml.com/](https://plantuml.com/)
- **C4 Model Guide**: [https://c4model.com/](https://c4model.com/)
- **PlantUML C4**: [https://github.com/plantuml-stdlib/C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML)

## 📖 Understanding the Diagrams

### Color Coding

In C4 diagrams:
- **Light Blue**: Internal systems/containers you control
- **Gray**: External systems/services
- **Blue Persons**: Users of the system
- **Arrows**: Relationships and data flow

### Reading Tips

1. **Follow the arrows**: They show the direction of interaction
2. **Read the labels**: They explain what data flows and how
3. **Look at boundaries**: Boxes show system/container boundaries
4. **Check the legend**: Usually at the bottom of the diagram

### Common Questions

**Q: Why PlantUML instead of drawing tools like Lucidchart?**
A: PlantUML is text-based, so it:
- Version controls nicely with Git
- Can be reviewed in pull requests
- Stays in sync with code
- No proprietary lock-in

**Q: Can I convert these to PNG/SVG?**
A: Yes! Use PlantUML command line or VS Code export.

**Q: Do I need Java?**
A: Only for command-line rendering. Online editors work without Java.

**Q: How often should diagrams be updated?**
A: Update diagrams when making architectural changes, ideally before implementing.

## 🔍 Troubleshooting

### Diagram Won't Render

**Issue**: Syntax error in PlantUML code

**Solution**:
1. Check for missing `@startuml` or `@enduml`
2. Verify all parentheses are balanced
3. Check for typos in keywords
4. Use online editor to get better error messages

### External Includes Not Loading

**Issue**: `!include` statement fails

**Solution**:
1. Check internet connection
2. Use local copy of C4 PlantUML files
3. Or switch to online editor which handles includes

### Diagram Too Large

**Issue**: Diagram is too complex to read

**Solution**:
1. Split into multiple diagrams
2. Use different abstraction levels
3. Focus on specific subsystems
4. Increase image resolution when exporting

## 📚 Additional Resources

### Documentation
- [C4_ARCHITECTURE.md](C4_ARCHITECTURE.md) - Complete architecture guide
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick reference for architecture
- [README.md](README.md) - This directory's README

### PlantUML Learning
- [PlantUML Getting Started](https://plantuml.com/starting)
- [C4 Model Documentation](https://c4model.com/)
- [PlantUML Cheat Sheet](https://ogom.github.io/draw_uml/plantuml/)

### Architecture Learning
- [C4 Model Introduction](https://www.youtube.com/watch?v=x2-rSnhpw0g)
- [Software Architecture Guide](https://martinfowler.com/architecture/)

## 💡 Tips and Best Practices

1. **Start simple**: Don't try to show everything in one diagram
2. **Use consistent naming**: Keep names consistent across diagrams
3. **Update regularly**: Keep diagrams in sync with code
4. **Include in reviews**: Review diagrams during code reviews
5. **Export for presentations**: Generate PNGs for documentation and presentations
6. **Version control**: Always commit diagram sources, not just images

---

**Need Help?** Open an issue or contact the development team.

**Last Updated**: 2025-12-15
