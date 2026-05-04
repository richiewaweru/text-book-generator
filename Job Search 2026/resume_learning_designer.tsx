import React from 'react';
import { Download } from 'lucide-react';

export default function LearningDesignerResume() {
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
          Learning experience designer with classroom expertise and technical literacy. Skilled at designing 
          objective-driven learning systems, scaffolding complex concepts for diverse learners, and using data to 
          iterate on instructional design. Experience spans in-person instruction, digital tool adoption, and 
          curriculum development. Seeking to build engaging, effective learning products that scale educational impact.
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
            Unique experiential learning model across seven global cities integrating active learning principles. 
            Relevant courses: Multimodal Communication, Data Collection & Analysis, Software Development, AI
          </p>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">LEARNING DESIGN & INSTRUCTION EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Covenant Prep | Middle School Science Teacher</p>
            <p className="text-gray-600">Hartford, CT</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Instructional Designer & STEM Educator | Sept 2024 - Dec 2025</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Designed and delivered 150+ objective-aligned learning experiences using backward design principles for 100+ students across 3 classes, achieving 85% mastery rate on quarterly standards-based assessments</li>
            <li>Built structured learning progressions using I Do/We Do/You Do scaffolding model across 16-week curriculum, supporting gradual release of responsibility and increasing independent task completion from 60% to 85%</li>
            <li>Implemented daily formative assessment system collecting 400+ data points weekly through exit tickets and checks for understanding to adjust instruction in real-time, improving week-over-week performance by 20%</li>
            <li>Integrated computational thinking and logic-based problem-solving into 40+ STEM lessons, developing critical thinking skills measured through 15% improvement in problem-solving assessment scores</li>
            <li>Piloted AI-supported instructional tools (ChatGPT, Claude for Education) in 8-week trial, reducing feedback delivery time by 30% while improving feedback quality scores from 3.2/5 to 4.5/5 based on student surveys</li>
            <li>Designed classroom management systems using positive behavior supports and clear routines that created calm learning environment, increasing on-task time by 25% and reducing disruptions by 40%</li>
            <li>Collaborated with 100+ families through weekly updates and quarterly conferences, maintaining 95% satisfaction rate and gathering continuous feedback that informed 12 instructional adjustments</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Minerva University | Capstone Teaching Assistant</p>
            <p className="text-gray-600">San Francisco, CA</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Curriculum Contributor & Academic Mentor | Sept 2023 - May 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Mentored 50 students through complex, multi-step capstone projects over 8 months using structured planning frameworks, resulting in 95% on-time completion rate (vs 78% prior year average)</li>
            <li>Designed feedback frameworks with 5 milestone checkpoints and clear rubrics to support student progress and identify learning gaps, reducing need for major revisions by 35%</li>
            <li>Modeled analytical thinking and metacognitive strategies through 200+ individual consultations, helping students develop self-directed learning skills measured through reflection surveys</li>
            <li>Contributed to curriculum development by organizing 100+ resources, analyzing student feedback from 50 surveys, and recommending 8 improvements adopted by faculty for next cohort</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Breakthrough Twin Cities | Science Tutor</p>
            <p className="text-gray-600">Twin Cities, MN</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Academic Support Specialist | June 2023 - August 2023</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Delivered scaffolded STEM instruction to 25+ students tailored to individual learning styles and prior knowledge, achieving 80% improvement in pre/post assessment scores</li>
            <li>Conducted diagnostic assessments to identify misconceptions and designed targeted 30-45 minute interventions addressing specific learning gaps, reducing time-to-mastery by 30%</li>
            <li>Built rapport and motivation with students through culturally responsive teaching practices, resulting in 90% attendance rate and 4.5/5 student satisfaction scores</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">PRODUCT & SYSTEMS DESIGN EXPERIENCE</h2>
        
        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">Roommate Organizer Platform | Product Lead</p>
            <p className="text-gray-600">Minerva University</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">Jan 2024 - Apr 2024</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Conducted 20 user research interviews to identify behavioral patterns and pain points, discovering 80% of users struggled with task coordination and 65% cited communication breakdowns</li>
            <li>Designed user flows and interaction patterns that reduced cognitive load by 40% (measured through task completion time) and increased successful task completion from 65% to 90% in user testing</li>
            <li>Built and iterated on core features through 3 rounds of user testing with 15 participants, incorporating feedback to improve usability scores from 60/100 to 82/100 on System Usability Scale</li>
          </ul>
        </div>

        <div className="mb-4">
          <div className="flex justify-between">
            <p className="font-semibold">FreezeCrowd | Marketing & Growth Associate</p>
            <p className="text-gray-600">New York, NY</p>
          </div>
          <p className="text-gray-600 text-sm mb-2">June 2022 - Sept 2022</p>
          <ul className="list-disc ml-5 text-gray-700 space-y-1">
            <li>Analyzed user engagement data from 1,000+ sessions to identify 3 onboarding friction points causing 35% drop-off rate</li>
            <li>A/B tested 15 messaging variations across email and landing pages to improve clarity, increasing app registrations by 15% and improving comprehension scores</li>
          </ul>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">CORE COMPETENCIES</h2>
        <div className="grid grid-cols-2 gap-4 text-gray-700">
          <div>
            <p className="font-semibold mb-1">Instructional Design:</p>
            <p className="text-sm">Backward design (Wiggins & McTighe), Learning objectives (Bloom's Taxonomy), Assessment design (formative & summative), Scaffolding & differentiation, Feedback systems, Learner motivation (ARCS model)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Learning Science:</p>
            <p className="text-sm">Cognitive load theory, Active learning principles, Spaced repetition, Metacognition & self-regulation, Culturally responsive pedagogy, Universal Design for Learning (UDL)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Educational Technology:</p>
            <p className="text-sm">LMS platforms (Canvas, Google Classroom, Moodle), Video creation (Loom, Camtasia), Interactive content tools, AI tutoring platforms, Assessment platforms (Formative, Kahoot, Quizizz)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Research & Iteration:</p>
            <p className="text-sm">User research methods, Learning analytics, A/B testing, Data visualization, Continuous improvement, Usability testing</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Technical Skills:</p>
            <p className="text-sm">HTML/CSS basics, SCORM packaging concepts, Articulate Storyline/Rise (familiar), Adobe Creative Suite basics, Data analysis (Excel, Google Sheets)</p>
          </div>
          <div>
            <p className="font-semibold mb-1">Project Management:</p>
            <p className="text-sm">ADDIE & SAM models, Agile for learning design, Asana, Trello, Notion, Stakeholder collaboration, Clear documentation</p>
          </div>
        </div>
      </div>

      <div className="border-t-2 border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-bold text-gray-900 mb-3">TECHNICAL TOOLS & PLATFORMS</h2>
        <p className="text-gray-700 text-sm leading-relaxed">
          <span className="font-semibold">Learning Platforms:</span> Canvas, Google Classroom, Moodle (familiar), Blackboard (familiar) · 
          <span className="font-semibold">Content Creation:</span> Loom, Canva, Google Slides, PowerPoint, Camtasia (familiar), Articulate (learning) · 
          <span className="font-semibold">Assessment:</span> Formative, Kahoot, Quizizz, Google Forms · 
          <span className="font-semibold">Collaboration:</span> Google Workspace, Microsoft Office, Slack, Zoom, Miro · 
          <span className="font-semibold">AI Tools:</span> ChatGPT, Claude, AI educational platforms · 
          <span className="font-semibold">Data:</span> Excel, Google Sheets, Airtable, basic statistics · 
          <span className="font-semibold">Languages:</span> English (Fluent), Swahili (Fluent)
        </p>
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded border border-blue-200">
        <p className="text-sm text-blue-900">
          <strong>Customization Tips:</strong> For corporate L&D roles, emphasize adult learning principles and 
          business impact metrics. For EdTech product roles, emphasize user research and product iteration. For 
          curriculum design roles, emphasize standards alignment and backward design. Always add specific tools 
          from job description (Articulate, Storyline, Rise, Adobe Captivate, etc.).
        </p>
      </div>
    </div>
  );
}