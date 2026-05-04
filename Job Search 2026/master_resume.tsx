import React from 'react';
import { Download, Info } from 'lucide-react';

export default function MasterResume() {
  return (
    <div className="max-w-4xl mx-auto p-8 bg-white">
      <div className="mb-6 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">RICHARD WAWERU MAINA</h1>
          <p className="text-gray-600 mt-1">Hartford, CT · rmainawaweru@gmail.com · LinkedIn · 415-312-6723</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          <Download size={16} />
          <span className="text-sm">Download PDF</span>
        </button>
      </div>

      <div className="border-t-2 border-gray-300 pt-4">
        <h2 className="text-xl font-bold text-gray-900 mb-3">PROFESSIONAL SUMMARY</h2>
        <p className="text-gray-700 leading-relaxed">
          Technical problem-solver with experience spanning financial operations, systems implementation, and 
          customer-facing technical roles. Skilled at understanding complex technical architectures, translating 
          requirements into actionable solutions, and designing scalable processes. Strong foundation in data analysis, 
          financial systems, and cross-functional collaboration. Combines technical literacy with exceptional 
          communication skills to bridge technical and business stakeholders. Experienced working across global contexts 
          with diverse teams.
        </p>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">EDUCATION</h2>
        <div className="mb-3">
          <div className="flex justify-between">
            <p className="font-semibold">Minerva University</p>
            <p className="text-gray-600">San Francisco, CA</p>
          </div>
          <div className="flex justify-between">
            <p className="text-gray-700">Bachelor of Science in Computational Sciences and Economics (Double Major)</p>
            <p className="text-gray-600">Sept 2020 - May 2024</p>
          </div>
          <p className="text-gray-600 text-sm mt-1">
            Global experiential learning across 5 cities (San Francisco, Nairobi, Berlin, Hyderabad, Buenos Aires). 
            Relevant courses: Software Development, AI/ML, Data Analysis, Statistics, Economics, Systems Thinking
          </p>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">TECHNICAL & SYSTEMS EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Productivity Integration Platform | Independent Project</p>
            <p className="text-gray-600">Remote</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Systems Architect & Developer | Jan 2026 - Present</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Designed system architecture for productivity tool integration platform, mapping data flows across 5+ tools (task managers, calendars, note-taking apps) to synthesize actionable insights</li>
            <li>Conducted extensive market research and user interviews to identify integration gaps causing 40% productivity loss from context switching</li>
            <li>Defined technical requirements including API integrations, data models, and processing workflows for cross-platform data synthesis</li>
            <li>Currently implementing MVP using AI-assisted development and modern frameworks, iterating based on technical validation and user feedback</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Sawalands | Founder & Technical Lead</p>
            <p className="text-gray-600">Remote</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Apr 2025 - Jun 2025</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Led technical planning for land transaction platform, evaluating framework options (Django vs Flask, PostgreSQL vs MongoDB) based on scalability, team capabilities, and feature requirements</li>
            <li>Designed system architecture and data models to support group coordination, document management, and payment tracking across multi-party transactions</li>
            <li>Conducted regulatory research across 3 Kenyan counties to ensure technical solution met compliance requirements</li>
            <li>Created comprehensive technical documentation including system diagrams, API specifications, and database schemas</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Roommate Organizer Platform | Technical Lead & Product Manager</p>
            <p className="text-gray-600">Minerva University</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Jan 2024 - Apr 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Led full-stack development of residential management tool using Python (Flask), JavaScript, HTML/CSS, and SQLite for 4-person team over 14 weeks</li>
            <li>Made technical architecture decisions including framework selection, database design, and authentication implementation based on scalability and security requirements</li>
            <li>Wrote technical documentation covering API endpoints, data models, user flows, and deployment procedures</li>
            <li>Conducted 20 user interviews to define requirements, translated findings into technical specifications, and coordinated implementation across team</li>
            <li>Delivered functional prototype with user authentication, announcements, issue tracking, and document management features</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Covenant Prep | STEM Educator & Technical Systems Lead</p>
            <p className="text-gray-600">Hartford, CT</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Sept 2024 - Dec 2025</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Designed and implemented scalable learning system serving 100+ students, achieving 85% mastery rate through data-driven iteration and structured workflows</li>
            <li>Set up and managed Google Classroom LMS, configuring user permissions, integrations, and automated workflows for assignment distribution and grade tracking</li>
            <li>Provided technical support for faculty and students, troubleshooting system issues including drive recovery, user setup, and software installation</li>
            <li>Piloted AI-powered tools (ChatGPT, Claude) in 8-week trial, documenting technical implementation, measuring 30% efficiency improvement, and presenting ROI analysis to leadership</li>
            <li>Collected and analyzed 400+ weekly data points through systematic feedback loops to identify process bottlenecks and optimize outcomes</li>
            <li>Served as primary liaison for 100+ stakeholders, maintaining 95% satisfaction rate through clear technical communication and proactive issue resolution</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">FINANCIAL OPERATIONS & CUSTOMER SUCCESS EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Equity Bank Limited | Financial Services Associate</p>
            <p className="text-gray-600">Nairobi, Kenya</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Feb 2019 - Oct 2019</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Operated enterprise accounting system (Finserv) to process 100+ daily transactions across multiple financial instruments (cash, cheques, transfers) with 99.5% accuracy</li>
            <li>Enforced AML (Anti-Money Laundering) compliance by identifying suspicious activity patterns, conducting enhanced due diligence, and filing required regulatory reports</li>
            <li>Onboarded 200+ new clients to banking systems over 8 months, providing technical training and ensuring successful adoption of digital banking tools</li>
            <li>Achieved top customer satisfaction scores (5/5 KPI) for 8 consecutive months through clear technical communication and consultative problem-solving</li>
            <li>Cross-sold financial products to 30% of clients (vs 18% team average) by conducting discovery conversations, identifying needs, and explaining product value propositions</li>
            <li>Troubleshot customer technical issues with online banking, mobile apps, and account access, escalating complex cases appropriately</li>
            <li>Maintained strict operational controls and audit compliance in high-stakes financial environment</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">FreezeCrowd | Marketing & Growth Associate</p>
            <p className="text-gray-600">New York, NY</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">June 2022 - Sept 2022</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Analyzed user engagement data from 1,000+ sessions in Google Analytics to identify 3 onboarding friction points causing 35% drop-off</li>
            <li>Executed 20+ A/B tests on email campaigns and landing pages, achieving 40% conversion rate through data-driven optimization</li>
            <li>Increased app registrations by 15% (300+ net new users) through systematic iteration on messaging strategy and user experience improvements</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Minerva University | Capstone Teaching Assistant</p>
            <p className="text-gray-600">San Francisco, CA</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Sept 2023 - May 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Mentored 50 students through complex technical projects over 8 months, achieving 95% on-time completion rate through structured guidance and systematic troubleshooting</li>
            <li>Provided technical support for research methodologies, data analysis, and statistical modeling across diverse project types</li>
            <li>Analyzed feedback patterns from 200+ student interactions to identify curriculum improvements, resulting in 8 recommendations adopted by faculty</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Breakthrough Twin Cities | STEM Tutor</p>
            <p className="text-gray-600">Twin Cities, MN</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">June 2023 - August 2023</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Delivered technical instruction to 25+ students, achieving 80% improvement in assessment scores through diagnostic problem-solving and tailored interventions</li>
            <li>Identified knowledge gaps systematically and designed targeted solutions, reducing time-to-competency by 30%</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">TECHNICAL SKILLS & COMPETENCIES</h2>
        <div className="grid grid-cols-2 gap-4 text-gray-700 text-sm">
          <div>
            <p className="font-semibold mb-1">Technical Architecture & Systems:</p>
            <p>System design, API architecture, Database design (SQL, NoSQL), Framework evaluation, Technical documentation, Data flow mapping, Integration patterns</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Programming & Development:</p>
            <p>Python, JavaScript, HTML/CSS, SQL, Git/GitHub, Can read/understand multiple languages, AI-assisted development, VS Code, Command line</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Data Analysis & Problem-Solving:</p>
            <p>Data manipulation (pandas, numpy), Data cleaning & feature extraction, Statistical analysis, Excel/Google Sheets (advanced), Data visualization, Problem formulation</p>
          </div>
          <div>
            <p className="font-semibold mb-1">AI/ML Understanding:</p>
            <p>LLM architectures, CNNs, LSTMs, Model evaluation, AI tool implementation, Prompt engineering, AI workflow design</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Financial Systems & Compliance:</p>
            <p>Enterprise accounting systems (Finserv), General Ledger concepts, AP/AR fundamentals, AML compliance, Transaction processing, Financial reporting, Audit procedures</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Business & Collaboration Tools:</p>
            <p>Google Workspace, Microsoft Office, Salesforce (basics), CRM concepts, Slack, Zoom, Asana, Trello, Notion, Jira (familiar), Miro</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Customer Success & Support:</p>
            <p>Technical troubleshooting, User onboarding, Training & enablement, Stakeholder communication, Issue diagnosis, Customer satisfaction tracking</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Process & Operations:</p>
            <p>Process design, Workflow optimization, Documentation, Project coordination, Metrics tracking, Cross-functional collaboration</p>
          </div>
        </div>
        <div className="mt-3 text-gray-700 text-sm">
          <p><span className="font-semibold">Languages:</span> English (Fluent), Swahili (Fluent)</p>
          <p><span className="font-semibold">Global Experience:</span> Lived and worked across 5 countries (USA, Kenya, Germany, India, Argentina)</p>
        </div>
      </div>

      <div className="mt-8 p-4 bg-green-50 rounded border border-green-200">
        <div className="flex items-start gap-2">
          <Info size={20} className="text-green-700 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-green-900">
            <p className="font-semibold mb-2">Master Resume - Customization Guide:</p>
            <p className="mb-2"><strong>For Technical Customer-Facing Roles (Solutions Engineer, Implementation):</strong> Lead with Roommate Organizer and Covenant Prep technical support bullets. Emphasize technical communication and troubleshooting.</p>
            <p className="mb-2"><strong>For Financial Systems Roles (Fintech, Accounting Software):</strong> Lead with Equity Bank experience. Emphasize Finserv system, AML compliance, and accounting concepts. Add QuickBooks/NetSuite/Xero as "familiar with similar accounting systems."</p>
            <p className="mb-2"><strong>For Product/Operations Roles:</strong> Lead with Sawalands and Productivity Platform. Emphasize systems thinking, requirements documentation, and cross-functional coordination.</p>
            <p><strong>Quick Customization (5 mins):</strong> Add 2-3 sentences at top of summary explaining interest in specific company/role. Reorder experience sections to put most relevant first. Add 1-2 company-specific tools to skills section.</p>
          </div>
        </div>
      </div>
    </div>
  );
}