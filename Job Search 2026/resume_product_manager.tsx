import React from 'react';
import { Download } from 'lucide-react';

export default function ProductManagerResume() {
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
          Product-minded professional with experience translating user needs into structured systems and measurable 
          outcomes. Skilled at defining requirements, conducting user research, iterating based on data, and 
          coordinating cross-functional execution. Background in computational sciences and education provides deep 
          user empathy combined with technical literacy. Seeking to build products that solve real problems at scale.
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
            Relevant courses: Software Development, Artificial Intelligence, Statistics & Data Visualization, 
            Startups & Big Ideas, Economics & Econometrics
          </p>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">PRODUCT EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Sawalands | Founder & Product Owner</p>
            <p className="text-gray-600">Remote</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Apr 2025 - Jun 2025</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Identified $2B+ market opportunity in Kenyan land transactions through 25+ customer discovery interviews and competitive analysis, uncovering 40-60 day coordination delays and 15-20% transaction failure rates</li>
            <li>Defined product vision and 12-month roadmap for digital platform to streamline group land purchases, prioritizing features by user value and technical feasibility using RICE framework</li>
            <li>Designed operational workflows and user journeys for buyer coordination, document management, and payment tracking to reduce transaction time by estimated 50%</li>
            <li>Conducted regulatory research across 3 Kenyan counties to validate legal constraints and ensure compliance in MVP scope</li>
            <li>Developed comprehensive product requirements documentation including 8 core user stories, success metrics (transaction completion rate, time-to-close, user satisfaction), and go-to-market strategy</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Roommate Organizer Platform | Product Lead</p>
            <p className="text-gray-600">Minerva University</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Jan 2024 - Apr 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Led end-to-end product development of residential management tool through competitive 14-week startup course, owning product strategy and hands-on implementation for 4-person team</li>
            <li>Conducted 20 user interviews with residents to identify unmet needs, discovering that 80% struggled with maintenance tracking and 65% cited communication breakdowns as top pain point</li>
            <li>Translated user insights into product requirements and prioritized 12 features using MoSCoW method, defining clear acceptance criteria and user flows for MVP</li>
            <li>Designed and implemented backend logic (Python/Flask) and frontend interfaces (JavaScript/HTML/CSS) for user authentication, announcements (3-5 per week capacity), issue tracking (status workflows), and document management (5GB storage)</li>
            <li>Coordinated cross-functional team using 2-week sprints with daily standups, sprint planning, and retrospectives while contributing 40% of codebase</li>
            <li>Delivered functional prototype demonstrating 95% of planned MVP features and presented to 30+ stakeholders, incorporating feedback into final iteration</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">PRODUCT-RELEVANT EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Covenant Prep | Middle School Science Teacher</p>
            <p className="text-gray-600">Hartford, CT</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Learning Systems Designer | Sept 2024 - Dec 2025</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Designed 150+ objective-driven learning experiences with clear success criteria and measurable outcomes for 100+ diverse users, achieving 85% mastery rate on quarterly assessments</li>
            <li>Implemented daily feedback loops using exit tickets (400+ data points collected) to identify friction points and iterate on experience design, improving week-over-week performance by 20%</li>
            <li>Piloted AI-supported tools to improve efficiency by 30%, documenting impact through A/B comparison and presenting ROI analysis to leadership, resulting in department-wide adoption</li>
            <li>Collaborated with 100+ stakeholders (families, administrators) through structured communication cadence, maintaining 95% satisfaction rate and gathering continuous feedback for improvement</li>
            <li>Built structured systems for engagement and behavior that increased on-task time by 25% and reduced disruptions by 40% compared to previous semester baseline</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Minerva University | Capstone Teaching Assistant</p>
            <p className="text-gray-600">San Francisco, CA</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Sept 2023 - May 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Mentored 50 students through multi-step projects over 8 months, defining clear milestones and success criteria that resulted in 95% on-time completion rate</li>
            <li>Supported curriculum development by organizing resources, identifying content gaps through student feedback analysis, and recommending 8 curriculum improvements adopted by faculty</li>
            <li>Gathered qualitative feedback from 200+ student interactions and identified patterns to inform instructional design improvements</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">FreezeCrowd | Marketing & Growth Associate</p>
            <p className="text-gray-600">New York, NY</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">June 2022 - Sept 2022</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Executed 20+ growth experiments using A/B testing on email subject lines, CTAs, and landing pages, achieving 40% conversion rate (8% above company benchmark)</li>
            <li>Analyzed user engagement data across 1,000+ sessions in Google Analytics to identify 3 major drop-off points in onboarding funnel</li>
            <li>Increased app registrations by 15% through data-driven iteration on messaging strategy and targeting, contributing to 300+ net new users</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Equity Bank Limited | Client Services Associate</p>
            <p className="text-gray-600">Nairobi, Kenya</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Feb 2019 - Oct 2019</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Achieved 5/5 customer satisfaction KPI for 8 consecutive months through deep understanding of client needs and clear communication</li>
            <li>Cross-sold products to 30% of engaged clients (vs 18% team average) by identifying pain points through discovery questions and recommending relevant solutions</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">CORE SKILLS & TOOLS</h2>
        <div className="grid grid-cols-2 gap-4 text-gray-700">
          <div>
            <p className="font-semibold mb-1">Product Management:</p>
            <p className="text-sm">User research & discovery, Requirements definition (user stories, acceptance criteria), Roadmap prioritization (RICE, MoSCoW), Feature scoping, A/B testing, User journey mapping, Competitive analysis</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Technical Skills:</p>
            <p className="text-sm">Python, JavaScript, HTML/CSS, SQL, Git, Software development fundamentals, API concepts, Data analysis (Excel, Google Sheets), Basic statistics</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Product Tools:</p>
            <p className="text-sm">Figma/Sketch (basic), Notion, Trello, Asana, Jira (familiar), Google Analytics, Miro (whiteboarding), Loom (documentation)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Collaboration & Process:</p>
            <p className="text-sm">Agile/Scrum methodologies, Cross-functional coordination, Stakeholder management, Technical documentation, Clear written/verbal communication</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Business & Strategy:</p>
            <p className="text-sm">Market research, Go-to-market strategy, Metrics definition (KPIs, OKRs), Customer discovery, Competitive positioning</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Languages:</p>
            <p className="text-sm">English (Fluent), Swahili (Fluent)</p>
          </div>
        </div>
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded border border-blue-200">
        <p className="text-sm text-blue-900">
          <strong>Customization Tips:</strong> Add 2-3 sentences at top of Professional Summary about why you're 
          interested in the specific company/product. For technical PM roles, emphasize your coding contributions. 
          Mirror their product development methodology (Shape Up, dual-track agile, etc.) if mentioned in job description.
        </p>
      </div>
    </div>
  );
}