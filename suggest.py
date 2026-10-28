import re

FIELDS = {
    "INFORMATION-TECHNOLOGY": (
        ["Software Developer", "Backend Developer", "Data Analyst"],
        ["TCS", "Infosys", "Wipro", "HCLTech", "Accenture", "Zoho"],
        ["python", "java", "sql", "git", "docker", "api", "linux", "javascript"]),
    "ENGINEERING": (
        ["Graduate Engineer Trainee", "Design Engineer", "Project Engineer"],
        ["L&T", "Tata Projects", "Siemens", "Bosch", "Mahindra"],
        ["autocad", "solidworks", "matlab", "project management", "quality", "maintenance", "design"]),
    "ACCOUNTANT": (
        ["Accountant", "Accounts Executive", "Audit Associate"],
        ["Deloitte", "KPMG", "EY", "PwC", "Grant Thornton"],
        ["tally", "gst", "excel", "taxation", "auditing", "reconciliation", "accounts payable"]),
    "ADVOCATE": (
        ["Legal Associate", "Legal Advisor", "Compliance Executive"],
        ["Cyril Amarchand Mangaldas", "AZB & Partners", "Khaitan & Co", "Trilegal"],
        ["litigation", "drafting", "contracts", "legal research", "compliance", "negotiation"]),
    "AGRICULTURE": (
        ["Agronomist", "Agri Field Officer", "Farm Manager"],
        ["IFFCO", "UPL", "Syngenta", "Godrej Agrovet", "BigHaat"],
        ["crop", "irrigation", "soil", "fertilizer", "farm management", "supply chain"]),
    "APPAREL": (
        ["Merchandiser", "Fashion Designer", "Quality Controller"],
        ["Raymond", "Arvind", "Myntra", "Aditya Birla Fashion", "Zudio"],
        ["merchandising", "textile", "pattern making", "sourcing", "quality control", "inventory"]),
    "ARTS": (
        ["Content Creator", "Illustrator", "Art Teacher"],
        ["Ogilvy", "Dentsu", "Pocket FM", "Byju's", "Netflix India"],
        ["photoshop", "illustrator", "creative", "storytelling", "design", "editing"]),
    "AUTOMOBILE": (
        ["Service Engineer", "Production Engineer", "Quality Engineer"],
        ["Maruti Suzuki", "Tata Motors", "Mahindra", "Hero MotoCorp", "Bajaj Auto"],
        ["diagnostics", "assembly", "quality", "maintenance", "cad", "lean manufacturing"]),
    "AVIATION": (
        ["Ground Staff", "Cabin Crew", "Operations Executive"],
        ["IndiGo", "Air India", "Akasa Air", "Vistara", "Air India SATS"],
        ["customer service", "safety", "operations", "communication", "ticketing", "crew"]),
    "BANKING": (
        ["Probationary Officer", "Relationship Manager", "Credit Analyst"],
        ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak"],
        ["loans", "kyc", "credit", "customer relationship", "risk", "sales"]),
    "BPO": (
        ["Customer Support Executive", "Process Associate", "Team Leader"],
        ["Concentrix", "Teleperformance", "Genpact", "Startek", "TaskUs"],
        ["customer support", "communication", "crm", "typing", "voice process", "problem solving"]),
    "BUSINESS-DEVELOPMENT": (
        ["Business Development Executive", "Account Manager", "Growth Associate"],
        ["Zomato", "Swiggy", "Razorpay", "Freshworks", "Info Edge"],
        ["lead generation", "crm", "negotiation", "sales", "market research", "client"]),
    "CHEF": (
        ["Commis Chef", "Sous Chef", "Kitchen Supervisor"],
        ["Taj Hotels", "ITC Hotels", "Oberoi", "Marriott", "Haldiram's"],
        ["menu", "food safety", "inventory", "kitchen", "plating", "costing"]),
    "CONSTRUCTION": (
        ["Site Engineer", "Quantity Surveyor", "Project Coordinator"],
        ["L&T", "Shapoorji Pallonji", "Tata Projects", "Godrej Properties", "DLF"],
        ["autocad", "estimation", "site supervision", "safety", "project management", "billing"]),
    "CONSULTANT": (
        ["Business Analyst", "Associate Consultant", "Management Trainee"],
        ["Deloitte", "EY", "Accenture", "McKinsey", "ZS Associates"],
        ["analysis", "excel", "presentation", "stakeholder", "strategy", "powerpoint"]),
    "DESIGNER": (
        ["UI/UX Designer", "Graphic Designer", "Product Designer"],
        ["Adobe", "Flipkart", "Zoho", "Swiggy", "PhonePe"],
        ["figma", "photoshop", "wireframe", "prototype", "typography", "user research"]),
    "DIGITAL-MEDIA": (
        ["Social Media Executive", "Content Writer", "SEO Executive"],
        ["Ogilvy", "WPP", "Times Internet", "InMobi", "Dentsu"],
        ["seo", "social media", "analytics", "content", "canva", "copywriting"]),
    "FINANCE": (
        ["Financial Analyst", "Investment Analyst", "FP&A Associate"],
        ["Goldman Sachs", "JP Morgan", "HDFC", "Bajaj Finserv", "Zerodha"],
        ["excel", "financial modeling", "valuation", "budgeting", "forecasting", "sql"]),
    "FITNESS": (
        ["Fitness Trainer", "Nutrition Coach", "Gym Manager"],
        ["Cult.fit", "Gold's Gym", "Anytime Fitness", "HealthifyMe"],
        ["training", "nutrition", "certification", "client", "workout", "wellness"]),
    "HEALTHCARE": (
        ["Staff Nurse", "Medical Coder", "Hospital Administrator"],
        ["Apollo Hospitals", "Fortis", "Max Healthcare", "Practo", "Manipal"],
        ["patient care", "clinical", "medical records", "healthcare", "emergency", "documentation"]),
    "HR": (
        ["HR Executive", "Talent Acquisition Specialist", "HR Generalist"],
        ["Naukri (Info Edge)", "Randstad", "TeamLease", "Accenture", "Wipro"],
        ["recruitment", "payroll", "onboarding", "employee engagement", "hris", "interviewing"]),
    "PUBLIC-RELATIONS": (
        ["PR Executive", "Communications Associate", "Media Relations Manager"],
        ["Adfactors PR", "Edelman", "Weber Shandwick", "Genesis BCW"],
        ["press release", "media relations", "communication", "branding", "event", "social media"]),
    "SALES": (
        ["Sales Executive", "Inside Sales Associate", "Territory Manager"],
        ["HUL", "ITC", "Reliance Retail", "Byju's", "Paytm"],
        ["b2b", "crm", "negotiation", "lead generation", "target", "customer relationship"]),
    "TEACHER": (
        ["School Teacher", "Subject Tutor", "Academic Coordinator"],
        ["DPS", "Ryan International", "Vedantu", "Unacademy", "Allen Career Institute"],
        ["lesson planning", "classroom management", "curriculum", "assessment", "teaching", "mentoring"]),
}

ACTION_VERBS = ["built", "developed", "designed", "created", "led", "implemented", "improved",
                "reduced", "increased", "optimized", "managed", "launched", "analyzed", "organized"]


def pretty(name):
    return name.replace("-", " ").title()


def analyze(text, top_field):
    t = text.lower()
    words = len(t.split())

    # (check name, passed?, tip if failed)
    checks = [
        ("Email", "@" in t,
         "Add your email address at the top of the resume."),
        ("LinkedIn / GitHub", "linkedin" in t or "github" in t,
         "Add a link to your LinkedIn or GitHub profile."),
        ("Summary", "summary" in t or "objective" in t or "profile" in t,
         "Write a 2-3 line Summary or Objective that matches your target role."),
        ("Education", "education" in t or "b.tech" in t or "degree" in t or "university" in t,
         "Add a clear Education section (degree, college, year)."),
        ("Skills section", "skills" in t,
         "Create a separate 'Skills' section so recruiters and ATS can find it easily."),
        ("Projects / Experience", any(k in t for k in ["project", "experience", "internship"]),
         "Add at least 2 projects or an internship / work experience."),
        ("Numbers and impact", len(re.findall(r"\d+\s?%|\d+\+", t)) >= 2,
         "Add numbers to your work, e.g. 'reduced load time by 30%' or '500+ users'."),
        ("Action verbs", sum(v in t for v in ACTION_VERBS) >= 3,
         "Start your bullet points with action words like 'Built', 'Developed', 'Improved'."),
        ("Good length", 200 <= words <= 800,
         "Keep your resume between 200 and 800 words (one page for freshers)."),
    ]

    passed = [c[0] for c in checks if c[1]]
    tips = [c[2] for c in checks if not c[1]]

    roles, companies, skills = FIELDS.get(top_field, ([], [], []))
    have = [s for s in skills if s in t]
    missing = [s for s in skills if s not in t]

    return {
        "field": pretty(top_field),
        "health": round(len(passed) / len(checks) * 100),
        "passed": passed,
        "failed": [c[0] for c in checks if not c[1]],
        "tips": tips,
        "roles": roles,
        "companies": companies,
        "skills_have": have,
        "skills_missing": missing,
    }