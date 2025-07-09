![](https://europe-west1-atp-views-tracker.cloudfunctions.net/working-analytics?notebook=contributing-guide)

# 🚀 Contributing to Agents Towards Production

Thank you for your interest in contributing! This guide will help you understand our standards and make the contribution process smooth.

## 📢 IMPORTANT: Signup and Tracking

**If your tutorial requires users to sign up for a service:**
1. Place signup instructions prominently at the beginning of your tutorial
2. Provide clear, step-by-step signup guidance
3. Always use UTM-tagged links for tracking (e.g., `https://service.com/?utm_source=agents-towards-production&utm_medium=github&utm_campaign=tutorial`)
4. Include screenshots of the signup process if applicable

This helps measure the impact of our tutorials and improves the user experience.

## 📂 Tutorial Structure

Each tutorial must be placed in the `tutorials/` directory and follow these naming and structure rules:

### Folder Naming
- Use lowercase letters
- Separate words with hyphens
- Example: `agent-with-your-tool-name`

### Required Files
Each tutorial folder should contain:

1. **Documentation** (one of the following):
   - a Jupyter notebook (`.ipynb`) - Interactive step-by-step guide
   - OR `tutorial.md` - Step-by-step integration guide
    

2. **Working Implementation Code** (Recommended):
   - `app.py` - Main application code (well-commented implementation)
   - OR equivalent main file with appropriate name
   - OR web-based application files (e.g., `index.html`, `main.js`) that can be run in a browser

3. **Dependencies**:
   - `requirements.txt`
     - All necessary dependencies
     - Specific versions recommended
     - Only required packages

4. **Additional Resources** (Optional but recommended):
   - `README.md` - Brief overview and quick start instructions
   - `assets/` folder for images, videos, and other media

### Example Tutorial Structure
Our existing `agent-with-streamlit-ui` tutorial demonstrates a good structure:

```
tutorials/
  agent-with-streamlit-ui/
    ├── app.py                        # Main application code
    ├── building-chatbot-notebook.ipynb   # Step-by-step Jupyter notebook tutorial
    ├── requirements.txt              # Dependencies
    └── assets/                       # Media files
        ├── streamlit_chatbot.PNG     # Screenshot for documentation
        └── streamlit_chatbot_video.mp4  # Demo video
```

## 📝 Notebook Structure

For new notebooks or significant additions to existing ones, please follow this structure:

1. **Title and Overview:** Clear title and brief overview of the technique.

2. **Detailed Explanation:** Cover motivation, key components, method details, and benefits.

3. **Visual Representation:** Include a diagram to visualize the technique. We recommend using Mermaid syntax for creating these diagrams:

   * Create a graph using Mermaid's graph TD (top-down) syntax
   * You can use Claude or other AI assistants to help you design the graph if needed
   * Paste your Mermaid code into [Mermaid Live Editor](https://mermaid.live/)
   * In the "Actions" tab of Mermaid Live Editor, download the SVG file of your diagram
   * Store the SVG file in the `assets/` folder within your tutorial directory (e.g., `tutorials/your-tutorial-name/assets/`)
   * Use an appropriate, descriptive name for the file
   * In your notebook, display the image using Markdown syntax:
     ```markdown
     ![Your Technique Name](./assets/your-technique-name.svg)
     ```

   This process ensures consistency in our visual representations and makes it easy for others to understand and potentially modify the diagrams in the future.

4. **Implementation:** Step-by-step Python implementation with clear comments and explanations.

5. **Usage Example:** Demonstrate the technique with a practical example.

6. **External Tool Integration:** If demonstrating external tool use or website interactions, provide step-by-step screenshots of each action. Place these screenshots in the assets folder and ensure they clearly show the process flow.

7. **Additional Considerations:** Discuss limitations, potential improvements, or specific use cases.

## ✨ Notebook Best Practices

To ensure consistency and readability across all notebooks:

1. **Code Cell Descriptions:** Each code cell should be preceded by a markdown cell with a clear, concise title describing the cell's content or purpose.

2. **Clear Unnecessary Outputs:** Before committing your notebook, clear all unnecessary cell outputs. This helps reduce file size and avoids confusion from outdated results.

3. **Consistent Formatting:** Maintain consistent formatting throughout the notebook, including regular use of markdown headers, code comments, and proper indentation.

## 💻 Code Quality and Readability

To ensure the highest quality and readability of our code:

1. **Write Clean Code:** Follow best practices for clean, readable code.
2. **Use Comments:** Add clear and concise comments to explain complex logic.
3. **Format Your Code:** Use consistent formatting throughout your contribution.
4. **Language Model Review:** After completing your code, consider passing it through a language model for additional formatting and readability improvements. This extra step can help make your code even more accessible and maintainable.

## 📚 Documentation

Clear documentation is crucial. Whether you're improving existing docs or adding new ones, follow this process:

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/AmazingFeature`
3. Commit your changes: `git commit -m 'Add some AmazingFeature'`
4. Push to the branch: `git push origin feature/AmazingFeature`
5. Open a pull request

## ✅ Pre-PR Checklist

Before submitting your PR, ensure:

- [ ] Tutorial follows the required structure
- [ ] All required files are present
- [ ] Code runs without errors
- [ ] Dependencies are listed in requirements.txt with appropriate versions
- [ ] Documentation is clear and complete
- [ ] No sensitive information included (like API keys)
- [ ] Code is well-commented
- [ ] Tutorial is self-contained
- [ ] Uses current library versions (e.g., OpenAI v1+ client)

## 🎯 Final Notes

We're grateful for all our contributors and excited to see how you'll help expand the world's most comprehensive resource for production-ready AI agents. Don't hesitate to ask questions if you're unsure about anything.

Let's harness our collective knowledge and creativity to push the boundaries of AI agent technology together!

**Happy contributing!** 🚀
