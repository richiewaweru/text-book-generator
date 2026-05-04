import React from 'react';
import { Download } from 'lucide-react';

export default function SolutionsEngineerResume() {
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
          Technical educator and communicator with proven ability to translate complex concepts for diverse audiences. 
          Experienced in delivering structured demonstrations, adapting communication styles based on audience needs, 
          and using feedback to optimize outcomes. Strong foundation in computational thinking, data analysis, and 
          technology adoption. Seeking to leverage teaching expertise and technical literacy in a customer-facing 
          technical role.
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
            Relevant courses: Software Development, Artificial Intelligence, Machine Learning, Data Analysis, 
            Statistics and Data Visualization
          </p>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">TECHNICAL DEMONSTRATION & CUSTOMER COMMUNICATION EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Covenant Prep | Middle School Science Teacher</p>
            <p className="text-gray-600">Hartford, CT</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">STEM Educator & Technical Adoption Lead | Sept 2024 - Dec 2025</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Delivered 150+ structured technical demonstrations to 100+ diverse users across 16 weeks, adapting presentation style based on prior knowledge and achieving 85% concept mastery rate on assessments</li>
            <li>Piloted AI-powered instructional tools (ChatGPT, Claude, educational AI platforms), achieving 30% efficiency improvement in feedback delivery; documented ROI and presented findings to leadership for scaled adoption</li>
            <li>Served as primary liaison for 100+ families, maintaining 95% satisfaction rate through clear technical communication, proactive issue resolution, and consistent follow-through on commitments</li>
            <li>Conducted 400+ formative assessments using exit tickets and checks for understanding to identify comprehension gaps and adjusted approach in real-time, improving week-over-week performance by 20%</li>
            <li>Built trust with initially skeptical stakeholders by delivering data-backed recommendations, active listening, and demonstrating measurable outcomes within first 6 weeks</li>
            <li>Managed logistics for 5 school-wide technical initiatives, coordinating across departments and ensuring on-time, on-budget delivery</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Minerva University | Capstone Technical Advisor</p>
            <p className="text-gray-600">San Francisco, CA</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Sept 2023 - May 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Mentored 50+ students through complex technical projects, conducting 200+ structured feedback sessions to diagnose blockers and guide implementation strategies</li>
            <li>Translated technical research methodologies and statistical concepts for non-technical stakeholders, enabling cross-functional project success</li>
            <li>Achieved 95% project completion rate by establishing clear milestones, regular check-ins, and proactive intervention when students encountered technical challenges</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Breakthrough Twin Cities | STEM Tutor & Curriculum Consultant</p>
            <p className="text-gray-600">Twin Cities, MN</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">June 2023 - August 2023</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Delivered one-on-one technical instruction to 25+ students, achieving 80% improvement in assessment scores through tailored communication approaches</li>
            <li>Identified knowledge gaps through diagnostic questioning and provided targeted interventions, reducing time-to-competency by 30%</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">TECHNICAL PROJECT EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Roommate Organizer Platform | Technical Product Contributor</p>
            <p className="text-gray-600">Minerva University</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Jan 2024 - Apr 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Conducted 15+ user interviews to identify technical pain points in residential management workflows, synthesizing findings into actionable product requirements</li>
            <li>Contributed to full-stack development using Python (Flask), JavaScript, HTML/CSS, and SQLite to build functional prototype with user authentication, announcements, and issue tracking</li>
            <li>Delivered 3 product demonstrations to stakeholders, explaining technical capabilities and gathering feedback that shaped final feature set</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">FreezeCrowd | Marketing & Growth Associate</p>
            <p className="text-gray-600">New York, NY</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">June 2022 - Sept 2022</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Executed 20+ email campaigns achieving 40% registration conversion rate through A/B testing subject lines, messaging, and CTAs</li>
            <li>Analyzed user engagement metrics in Google Analytics to identify friction points, implementing 5 optimizations that increased app registrations by 15%</li>
            <li>Collaborated with product team to communicate user feedback and inform feature prioritization</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Equity Bank Limited | Client Services Associate</p>
            <p className="text-gray-600">Nairobi, Kenya</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Feb 2019 - Oct 2019</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Processed 100+ daily transactions with 99.5% accuracy in high-stakes financial environment, maintaining strict compliance with banking regulations</li>
            <li>Achieved top customer satisfaction scores (5/5 KPI) for 8 consecutive months through clear communication and proactive problem-solving</li>
            <li>Cross-sold financial products to 30% of clients by identifying needs through discovery conversations and explaining product value propositions</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">TECHNICAL SKILLS & TOOLS</h2>
        <div className="grid grid-cols-2 gap-4 text-gray-700">
          <div>
            <p className="font-semibold mb-1">Programming & Development:</p>
            <p className="text-sm">Python, JavaScript, HTML/CSS, SQL, Git/GitHub, VS Code, Command line basics</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Data & Analytics:</p>
            <p className="text-sm">Excel (advanced formulas, pivot tables), Google Sheets, Basic statistical analysis, Data visualization, Google Analytics</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Business & Productivity Tools:</p>
            <p className="text-sm">Google Workspace (Docs, Sheets, Slides, Drive), Microsoft Office Suite, Slack, Zoom, Asana, Trello, Notion</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Technical Communication:</p>
            <p className="text-sm">Technical demonstrations, Documentation, Stakeholder presentations, User training, Screen recording tools</p>
          </div>
          <div>
            <p className="font-semibold mb-1">AI & Modern Tools:</p>
            <p className="text-sm">ChatGPT, Claude, AI-powered educational platforms, Learning management systems (Google Classroom, Canvas)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Languages:</p>
            <p className="text-sm">English (Fluent), Swahili (Fluent)</p>
          </div>
        </div>
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded border border-blue-200">
        <p className="text-sm text-blue-900">
          <strong>Customization Tips:</strong> For each application, add 2-3 specific tools from the job description 
          (e.g., Salesforce, Zendesk, their product). Replace generic metrics with company-specific ones where 
          possible (e.g., if they mention "customer retention," emphasize your 95% satisfaction rate).
        </p>
      </div>
    </div>
  );
}