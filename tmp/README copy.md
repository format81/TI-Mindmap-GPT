<img src="logoTIMINDMAPGPT-small.png" alt="TI MINDMAP GPT" width="200" height="200"/>

Welcome to TI MINDMAP GPT, an AI-powered tool designed to help producing Threat Intelligence Mindmap.

**Introducing TI Mindmap** 
Navigating through lengthy blog posts, threat intelligence articles, or write-ups can be daunting, especially for cyber threat intelligence teams aiming to extract key insights efficiently. Enter TI Mindmap, a tool accessible through the Streamlit app platform. With just a URL as input, this service harnesses the power of OpenAI, Azure OpenAI and MistraAI to transform cumbersome content into concise, actionable summaries. But it doesn’t stop there. Utilizing sophisticated algorithms, TI Mindmap goes beyond mere text reduction, providing users with insightful encapsulations of crucial points and themes.
TI Mindmap is a tool developed using Large Language Models (LLMs). It's designed to assist cyber threat intelligence teams in quickly synthesizing and visualizing key information from various Threat Intelligence sources. 
The app operates on a 'Bring Your Own (LLM) Key' model, allowing users to leverage their own Large Language Models keys for personalized and efficient information processing. 
This tool aims to streamline the data analysis process, enabling teams to focus more on strategic decision-making and less on the cumbersome task of data mining.

App: [APP](https://ti-mindmap-gpt.streamlit.app/)

## Table of Contents
- [Project](#project)
- [Features](#features)
- [Know issues](#Knowissues)
- [Blog posts](#blogposts)
- [Contributing](#contributing)
- [License](#license)

## Project

If you find TI MINDMAP useful, please consider starring the repository on GitHub. 

## Features
- LLM supported: OpenAI, Azure OpenAI, MistralAI
- Summary in markdown format 
- Mindmap in Mermaid.js or MarkMap
- Tweet Mindmap
- IOCs extraction with VirusTotal IOCs enrichment
- Extract adversary tactics, techniques, and procedures
- Tactics, techniques and procedures by execution time
- Tactics, techniques and procedures timeline
- Embedded MITRE ATT&CK® Navigator
- AI Chat on your TI Article
- Mermaid live editor integration
- PDF Report: Your Intelligence, Concisely Captured
- Write-up screenshot
- STIX 2.1 report generator (The dedicated project [GenAI-STIX2.1-Generator](https://github.com/format81/GenAI-STIX2.1-Generator/) has been merged.)

## Know issues
A known issue occurs when clicking “Generate PDF”, causing the Streamlit app (1.35 at the time of writing this post) to reload and resulting in the loss of output previously generated. This issue is currently being addressed by Streamlit and is scheduled for resolution in the roadmap between August and October 2024. A new functionality titled “Don’t rerun when clicking st.download_button” is planned to mitigate this issue.

## Blog posts
1. [Introducing TI Mindmap GPT](https://medium.com/@antonio.formato/introducing-ti-mindmap-gpt-6f433f140488)
2. [Enhancing Cyber Threat Intelligence with TI Mindmap GPT: Integration of Azure OpenAI and advanced features](https://medium.com/microsoftazure/enhancing-cyber-threat-intelligence-with-ti-mindmap-gpt-integration-of-azure-openai-and-advanced-94121ed66ac4)
3. [What’s new in TI Mindmap | Feb 2024](https://medium.com/@antonio.formato/whats-new-in-ti-mindmap-feb-2024-14cf3b383833)
4. [What’s new in TI Mindmap | Mar 2024](https://medium.com/@antonio.formato/whats-new-in-ti-mindmap-mar-2024-3712f38c6dd6)
5. [What’s new in TI Mindmap | April 2024](https://medium.com/@antonio.formato/whats-new-in-ti-mindmap-april-2024-29e1bfb88ae5)
6. [What’s new in TI Mindmap | May 2024](https://medium.com/@antonio.formato/whats-new-in-ti-mindmap-may-2024-3af9e8d90be8)
7. [What’s new in TI Mindmap | Sep 2024](https://medium.com/@antonio.formato/whats-new-in-ti-mindmap-sep-2024-1f3ce3197789)

### Version 0.1

Initial release of the application.

## Contributing

The project is open to external contributions. Pull requests are welcome. 
Here's how you can help:

- **Testing and Feedback**: Try the tool and share your insights to improve its performance and usability.
- **Improving Prompts**: Help refine the AI prompts for better extraction and accuracy of unstructured cyber threat intelligence data.
- **Extending Functionality**: Build additional features, or improve existing workflows.
- **Open Discussions**: Join the conversation to explore innovative use cases and share your ideas.

Your contributions will help make this project more robust and impactful. Thank you for your support!

## License

[GNU GPLv3](https://choosealicense.com/licenses/gpl-3.0/)