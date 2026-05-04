import React from 'react';
import { Download } from 'lucide-react';

export default function ImplementationSpecialistResume() {
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
          Customer-focused implementation professional with proven ability to onboard diverse users to complex systems. 
          Experienced in designing structured adoption processes, diagnosing friction points, and ensuring successful 
          outcomes through clear communication and technical support. Strong background in education provides deep 
          understanding of behavior change, user adoption, and scaffolded learning. Seeking to drive customer success 
          through thoughtful implementation and strategic partnership.
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
            Relevant courses: Software Development, Data Analysis, Statistics, Economics, Multimodal Communication
          </p>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">IMPLEMENTATION & CUSTOMER SUCCESS EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Covenant Prep | Middle School Science Teacher</p>
            <p className="text-gray-600">Hartford, CT</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Program Implementation Lead | Sept 2024 - Dec 2025</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Onboarded 100+ students to structured learning systems across 3 classes over 16 weeks, achieving 85% proficiency rate through clear expectations, scaffolded training materials, and weekly check-ins</li>
            <li>Designed and implemented onboarding process with 5 defined milestones and success checkpoints, reducing time-to-proficiency from 8 weeks to 6 weeks and increasing user confidence scores from 3.1/5 to 4.3/5</li>
            <li>Served as primary point of contact for 100+ families, managing expectations through weekly communication, troubleshooting 50+ issues proactively, and maintaining 95% stakeholder satisfaction rate measured through quarterly surveys</li>
            <li>Led adoption of new AI-powered tools across 8-week pilot program, managing change management process including training sessions, documentation, and ongoing support, achieving 30% efficiency gains and 85% user adoption rate</li>
            <li>Used daily check-ins and 400+ weekly data points from formative assessments to identify adoption barriers early, reducing escalations by 40% through proactive intervention within 24-48 hours</li>
            <li>Built trust with diverse stakeholders through consistent communication cadence (weekly updates, bi-weekly 1:1s), transparent issue resolution (avg 2-day response time), and demonstrated commitment to success outcomes</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Minerva University | Capstone Project Advisor</p>
            <p className="text-gray-600">San Francisco, CA</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Sept 2023 - May 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Guided 50 students through complex project implementations over 8 months, breaking down technical requirements into 5-7 manageable phases with clear deliverables and timelines</li>
            <li>Conducted 200+ structured planning sessions to define clear goals, success criteria, and risk mitigation strategies, resulting in 95% on-time completion rate (vs 78% prior year)</li>
            <li>Diagnosed 150+ blockers through active listening and diagnostic questioning, recommending solutions aligned with project constraints and reducing average resolution time from 5 days to 2 days</li>
            <li>Maintained consistent bi-weekly communication cadence to ensure accountability and proactive issue resolution, achieving 4.5/5 satisfaction rating from students</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Breakthrough Twin Cities | Academic Support Specialist</p>
            <p className="text-gray-600">Twin Cities, MN</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">June 2023 - August 2023</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Provided one-on-one implementation support for 25+ students learning new STEM concepts and tools, achieving 80% improvement in assessment scores through personalized onboarding</li>
            <li>Adapted onboarding approach based on individual user needs, prior experience, and learning styles using diagnostic assessment framework, reducing time-to-competency by 30%</li>
            <li>Identified knowledge gaps through 100+ diagnostic assessments and designed targeted 30-45 minute training interventions with clear success metrics</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Equity Bank Limited | Client Services & Onboarding Specialist</p>
            <p className="text-gray-600">Nairobi, Kenya</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Feb 2019 - Oct 2019</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Onboarded 200+ new clients to banking systems and products over 8 months, ensuring smooth transition through structured training, documentation, and follow-up support</li>
            <li>Achieved top customer satisfaction scores (5/5 KPI) for 8 consecutive months through clear communication, proactive issue resolution (avg 1-day response time), and personalized service</li>
            <li>Identified client needs through 30-minute discovery conversations using consultative approach and recommended appropriate product solutions, achieving 30% cross-sell adoption rate (vs 18% team average)</li>
            <li>Processed 100+ daily transactions with 99.5% accuracy in high-stakes financial environment requiring precision, compliance adherence, and attention to detail</li>
            <li>Reduced onboarding time from 45 minutes to 30 minutes by creating streamlined training materials and process documentation</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">TECHNICAL PROJECT & SYSTEMS EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Roommate Organizer Platform | Product Coordinator</p>
            <p className="text-gray-600">Minerva University</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Jan 2024 - Apr 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Conducted 20 user interviews to understand workflow pain points and requirements, synthesizing findings into product requirements document with 12 prioritized features</li>
            <li>Documented user workflows, technical requirements, and acceptance criteria to guide implementation and ensure stakeholder alignment across 4-person team</li>
            <li>Coordinated cross-functional team deliverables using 2-week sprints with daily standups, maintaining 95% on-time delivery rate over 14 weeks</li>
            <li>Contributed to technical implementation and facilitated 3 rounds of user testing with 15 participants, incorporating feedback to improve usability scores by 35%</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Sawalands | Operations & Strategy Lead</p>
            <p className="text-gray-600">Remote</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Apr 2025 - Jun 2025</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Conducted 25+ stakeholder interviews and market research to identify operational bottlenecks causing 40-60 day transaction delays in land purchase processes</li>
            <li>Designed operational workflows to support group land purchases, mapping 8 core user journeys and defining 15 process improvement opportunities</li>
            <li>Developed foundational implementation documentation including platform objectives, user onboarding flows, training materials outline, and operating procedures</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">FreezeCrowd | Marketing & User Acquisition Associate</p>
            <p className="text-gray-600">New York, NY</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">June 2022 - Sept 2022</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Supported user onboarding initiatives, executing 20+ email campaigns achieving 40% conversion rate through optimized messaging and clear CTAs</li>
            <li>Analyzed user engagement data from 1,000+ sessions to identify 3 major drop-off points causing 35% abandonment rate in onboarding funnel</li>
            <li>Increased app registrations 15% (300+ net new users) through data-driven improvements to acquisition and onboarding experience</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">CORE SKILLS & COMPETENCIES</h2>
        <div className="grid grid-cols-2 gap-4 text-gray-700">
          <div>
            <p className="font-semibold mb-1">Implementation & Onboarding:</p>
            <p className="text-sm">User onboarding design, Change management, Training & enablement, Process documentation, Adoption metrics tracking, Success criteria definition, Milestone planning</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Customer Success:</p>
            <p className="text-sm">Customer communication, Issue diagnosis & resolution, Proactive support, Relationship building, Satisfaction tracking, Health score monitoring, Risk identification</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Technical Skills:</p>
            <p className="text-sm">Technical troubleshooting, Software fundamentals, SQL basics, Data analysis (Excel, Google Sheets), API concepts, System integration understanding, CRM systems (Salesforce basics)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Project Management:</p>
            <p className="text-sm">Project coordination, Timeline management, Stakeholder communication, Documentation, Agile/Scrum basics, Asana, Trello, Notion, Jira (familiar)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Business Tools:</p>
            <p className="text-sm">Google Workspace, Microsoft Office Suite, Slack, Zoom, Loom (training videos), Miro (process mapping), Airtable, Monday.com (familiar)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Languages:</p>
            <p className="text-sm">English (Fluent), Swahili (Fluent)</p>
          </div>
        </div>
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded border border-blue-200">
        <p className="text-sm text-blue-900">
          <strong>Customization Tips:</strong> Add specific tools/platforms from job description (Salesforce, Zendesk, 
          Gainsight, ChurnZero, Intercom, etc.). Quantify your success metrics using language from their description 
          (time-to-value, adoption rate, health scores, NPS). For technical implementation roles, emphasize Roommate 
          Organizer technical work and troubleshooting skills.
        </p>
      </div>
    </div>
  );
}