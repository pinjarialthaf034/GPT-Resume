-- CareerCompass AI — Seed Data
-- 15+ careers, 40+ skills, multiple branches, assessments, projects

DO $$
DECLARE
    -- Skill IDs
    sk_python UUID; sk_java UUID; sk_cpp UUID; sk_c UUID;
    sk_html UUID; sk_css UUID; sk_js UUID; sk_react UUID; sk_node UUID;
    sk_sql UUID; sk_nosql UUID;
    sk_git UUID; sk_linux UUID; sk_docker UUID; sk_aws UUID;
    sk_cad UUID; sk_solidworks UUID; sk_ansys UUID; sk_thermodynamics UUID;
    sk_fluid UUID; sk_manufacturing UUID;
    sk_circuit UUID; sk_pcb UUID; sk_vlsi UUID; sk_microcontrollers UUID;
    sk_matlab UUID; sk_plc UUID; sk_scada UUID;
    sk_autocad UUID; sk_surveying UUID; sk_structural UUID; sk_concrete UUID;
    sk_estimation UUID;
    sk_ic_engines UUID; sk_vehicle_dynamics UUID; sk_ev UUID;
    sk_networking UUID; sk_cybersecurity UUID; sk_ml UUID; sk_data_analysis UUID;
    
    -- Career IDs
    c_sde UUID; c_frontend UUID; c_backend UUID; c_fullstack UUID;
    c_data_analyst UUID; c_devops UUID; c_cyber UUID;
    c_mech_design UUID; c_hvac UUID; c_manufacturing UUID;
    c_embedded UUID; c_vlsi UUID; c_electrical_design UUID;
    c_structural UUID; c_site_eng UUID;
    c_ev_eng UUID; c_automobile_design UUID;
    
    -- Project IDs
    p_web UUID; p_api UUID; p_cad UUID; p_circuit UUID; p_survey UUID;
    
    -- Assessment Qs
    q1 UUID; q2 UUID; q3 UUID; q4 UUID; q5 UUID;
    q6 UUID; q7 UUID; q8 UUID; q9 UUID; q10 UUID;
    q11 UUID; q12 UUID; q13 UUID; q14 UUID; q15 UUID;
BEGIN
    -- ==========================================
    -- 1. INSERT SKILLS (40+)
    -- ==========================================
    
    -- Computer / Software
    INSERT INTO skills (name, category) VALUES ('Python', 'Software') RETURNING id INTO sk_python;
    INSERT INTO skills (name, category) VALUES ('Java', 'Software') RETURNING id INTO sk_java;
    INSERT INTO skills (name, category) VALUES ('C++', 'Software') RETURNING id INTO sk_cpp;
    INSERT INTO skills (name, category) VALUES ('C', 'Software') RETURNING id INTO sk_c;
    INSERT INTO skills (name, category) VALUES ('HTML/CSS', 'Web') RETURNING id INTO sk_html;
    INSERT INTO skills (name, category) VALUES ('JavaScript', 'Web') RETURNING id INTO sk_js;
    INSERT INTO skills (name, category) VALUES ('React.js', 'Web') RETURNING id INTO sk_react;
    INSERT INTO skills (name, category) VALUES ('Node.js', 'Web') RETURNING id INTO sk_node;
    INSERT INTO skills (name, category) VALUES ('SQL', 'Database') RETURNING id INTO sk_sql;
    INSERT INTO skills (name, category) VALUES ('NoSQL', 'Database') RETURNING id INTO sk_nosql;
    INSERT INTO skills (name, category) VALUES ('Git', 'Tools') RETURNING id INTO sk_git;
    INSERT INTO skills (name, category) VALUES ('Linux', 'Tools') RETURNING id INTO sk_linux;
    INSERT INTO skills (name, category) VALUES ('Docker', 'DevOps') RETURNING id INTO sk_docker;
    INSERT INTO skills (name, category) VALUES ('AWS', 'Cloud') RETURNING id INTO sk_aws;
    INSERT INTO skills (name, category) VALUES ('Networking', 'IT') RETURNING id INTO sk_networking;
    INSERT INTO skills (name, category) VALUES ('Cybersecurity', 'IT') RETURNING id INTO sk_cybersecurity;
    INSERT INTO skills (name, category) VALUES ('Machine Learning', 'Data') RETURNING id INTO sk_ml;
    INSERT INTO skills (name, category) VALUES ('Data Analysis', 'Data') RETURNING id INTO sk_data_analysis;

    -- Mechanical
    INSERT INTO skills (name, category) VALUES ('AutoCAD (Mech)', 'Design') RETURNING id INTO sk_cad;
    INSERT INTO skills (name, category) VALUES ('SolidWorks', 'Design') RETURNING id INTO sk_solidworks;
    INSERT INTO skills (name, category) VALUES ('ANSYS', 'Analysis') RETURNING id INTO sk_ansys;
    INSERT INTO skills (name, category) VALUES ('Thermodynamics', 'Core') RETURNING id INTO sk_thermodynamics;
    INSERT INTO skills (name, category) VALUES ('Fluid Mechanics', 'Core') RETURNING id INTO sk_fluid;
    INSERT INTO skills (name, category) VALUES ('Manufacturing Tech', 'Core') RETURNING id INTO sk_manufacturing;
    
    -- ECE / EEE
    INSERT INTO skills (name, category) VALUES ('Circuit Design', 'Core') RETURNING id INTO sk_circuit;
    INSERT INTO skills (name, category) VALUES ('PCB Design', 'Design') RETURNING id INTO sk_pcb;
    INSERT INTO skills (name, category) VALUES ('VLSI Design', 'Design') RETURNING id INTO sk_vlsi;
    INSERT INTO skills (name, category) VALUES ('Microcontrollers', 'Core') RETURNING id INTO sk_microcontrollers;
    INSERT INTO skills (name, category) VALUES ('MATLAB', 'Tools') RETURNING id INTO sk_matlab;
    INSERT INTO skills (name, category) VALUES ('PLC/SCADA', 'Automation') RETURNING id INTO sk_plc;
    
    -- Civil
    INSERT INTO skills (name, category) VALUES ('AutoCAD (Civil)', 'Design') RETURNING id INTO sk_autocad;
    INSERT INTO skills (name, category) VALUES ('Surveying', 'Core') RETURNING id INTO sk_surveying;
    INSERT INTO skills (name, category) VALUES ('Structural Analysis', 'Core') RETURNING id INTO sk_structural;
    INSERT INTO skills (name, category) VALUES ('Concrete Tech', 'Core') RETURNING id INTO sk_concrete;
    INSERT INTO skills (name, category) VALUES ('Estimation & Costing', 'Core') RETURNING id INTO sk_estimation;
    
    -- Automobile
    INSERT INTO skills (name, category) VALUES ('IC Engines', 'Core') RETURNING id INTO sk_ic_engines;
    INSERT INTO skills (name, category) VALUES ('Vehicle Dynamics', 'Core') RETURNING id INTO sk_vehicle_dynamics;
    INSERT INTO skills (name, category) VALUES ('Electric Vehicles (EV)', 'Core') RETURNING id INTO sk_ev;

    -- ==========================================
    -- 2. INSERT CAREERS (15+)
    -- ==========================================
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Software Developer', 'Builds and maintains software applications.', '{CSE,IT}', 7.0, 4.5, 'IT') RETURNING id INTO c_sde;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Frontend Developer', 'Creates user interfaces for web applications.', '{CSE,IT}', 6.5, 4.0, 'IT') RETURNING id INTO c_frontend;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Backend Developer', 'Develops server-side logic and databases.', '{CSE,IT}', 7.0, 5.0, 'IT') RETURNING id INTO c_backend;

    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Full Stack Developer', 'Develops both frontend and backend of web applications.', '{CSE,IT}', 7.5, 6.0, 'IT') RETURNING id INTO c_fullstack;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Data Analyst', 'Analyzes data to help companies make decisions.', '{CSE,IT}', 6.5, 4.0, 'IT') RETURNING id INTO c_data_analyst;

    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Cybersecurity Analyst', 'Protects systems and networks from cyber threats.', '{CSE,IT,ECE}', 7.0, 5.5, 'IT') RETURNING id INTO c_cyber;

    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Embedded Systems Engineer', 'Designs hardware/software for embedded devices.', '{ECE,EEE,CSE}', 7.5, 5.0, 'Electronics') RETURNING id INTO c_embedded;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('VLSI Design Engineer', 'Designs integrated circuits and chips.', '{ECE}', 8.0, 6.5, 'Electronics') RETURNING id INTO c_vlsi;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Mechanical Design Engineer', 'Designs mechanical parts using CAD tools.', '{MECHANICAL,AUTOMOBILE}', 7.0, 4.0, 'Manufacturing') RETURNING id INTO c_mech_design;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('HVAC Engineer', 'Designs heating, ventilation, and air conditioning systems.', '{MECHANICAL}', 6.5, 3.5, 'Construction') RETURNING id INTO c_hvac;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Manufacturing Engineer', 'Optimizes manufacturing processes.', '{MECHANICAL}', 6.5, 3.5, 'Manufacturing') RETURNING id INTO c_manufacturing;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Electrical Design Engineer', 'Designs electrical systems and layouts.', '{EEE}', 7.0, 4.0, 'Energy') RETURNING id INTO c_electrical_design;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Structural Engineer', 'Analyzes and designs structures like buildings/bridges.', '{CIVIL}', 7.5, 4.5, 'Construction') RETURNING id INTO c_structural;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Site Engineer', 'Manages construction projects on site.', '{CIVIL}', 6.0, 3.0, 'Construction') RETURNING id INTO c_site_eng;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('Automobile Design Engineer', 'Designs automotive components.', '{AUTOMOBILE,MECHANICAL}', 7.0, 4.5, 'Automotive') RETURNING id INTO c_automobile_design;
    
    INSERT INTO careers (title, description, branches, min_cgpa, avg_salary_lpa, industry)
    VALUES ('EV Engineer', 'Develops systems for electric vehicles.', '{AUTOMOBILE,EEE,MECHANICAL}', 7.5, 5.5, 'Automotive') RETURNING id INTO c_ev_eng;


    -- ==========================================
    -- 3. MAP CAREER SKILLS (All 17 Careers)
    -- ==========================================
    
    -- SDE
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_sde, sk_java, 'intermediate', 1.5),
    (c_sde, sk_cpp, 'intermediate', 1.0),
    (c_sde, sk_sql, 'beginner', 1.0),
    (c_sde, sk_git, 'beginner', 0.5);

    -- Frontend
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_frontend, sk_html, 'intermediate', 1.0),
    (c_frontend, sk_js, 'intermediate', 1.5),
    (c_frontend, sk_react, 'beginner', 1.5),
    (c_frontend, sk_git, 'beginner', 0.5);

    -- Backend
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_backend, sk_python, 'intermediate', 1.5),
    (c_backend, sk_node, 'intermediate', 1.5),
    (c_backend, sk_sql, 'intermediate', 1.0),
    (c_backend, sk_docker, 'beginner', 0.8);

    -- Full Stack
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_fullstack, sk_js, 'intermediate', 1.2),
    (c_fullstack, sk_react, 'intermediate', 1.2),
    (c_fullstack, sk_node, 'intermediate', 1.2),
    (c_fullstack, sk_sql, 'beginner', 1.0);

    -- Data Analyst
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_data_analyst, sk_python, 'intermediate', 1.5),
    (c_data_analyst, sk_sql, 'intermediate', 1.5),
    (c_data_analyst, sk_data_analysis, 'intermediate', 1.5),
    (c_data_analyst, sk_ml, 'beginner', 0.8);

    -- Cybersecurity
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_cyber, sk_networking, 'intermediate', 1.5),
    (c_cyber, sk_cybersecurity, 'intermediate', 2.0),
    (c_cyber, sk_linux, 'intermediate', 1.0),
    (c_cyber, sk_python, 'beginner', 0.8);

    -- Embedded
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_embedded, sk_c, 'advanced', 2.0),
    (c_embedded, sk_microcontrollers, 'intermediate', 1.5),
    (c_embedded, sk_circuit, 'beginner', 1.0);

    -- VLSI Design
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_vlsi, sk_vlsi, 'advanced', 2.0),
    (c_vlsi, sk_circuit, 'intermediate', 1.5),
    (c_vlsi, sk_matlab, 'intermediate', 1.0);

    -- Mech Design
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_mech_design, sk_solidworks, 'intermediate', 2.0),
    (c_mech_design, sk_cad, 'intermediate', 1.5),
    (c_mech_design, sk_manufacturing, 'beginner', 1.0);

    -- HVAC
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_hvac, sk_thermodynamics, 'intermediate', 2.0),
    (c_hvac, sk_fluid, 'intermediate', 1.5),
    (c_hvac, sk_cad, 'beginner', 1.0);

    -- Manufacturing
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_manufacturing, sk_manufacturing, 'intermediate', 2.0),
    (c_manufacturing, sk_cad, 'beginner', 1.0),
    (c_manufacturing, sk_plc, 'beginner', 1.0);

    -- Electrical Design
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_electrical_design, sk_circuit, 'intermediate', 1.5),
    (c_electrical_design, sk_pcb, 'intermediate', 1.5),
    (c_electrical_design, sk_matlab, 'beginner', 1.0);

    -- Structural
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_structural, sk_structural, 'advanced', 2.0),
    (c_structural, sk_autocad, 'intermediate', 1.0),
    (c_structural, sk_concrete, 'intermediate', 1.0);

    -- Site Engineer
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_site_eng, sk_surveying, 'intermediate', 1.8),
    (c_site_eng, sk_estimation, 'intermediate', 1.5),
    (c_site_eng, sk_concrete, 'beginner', 1.0);

    -- Automobile Design
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_automobile_design, sk_solidworks, 'intermediate', 1.8),
    (c_automobile_design, sk_vehicle_dynamics, 'intermediate', 1.5),
    (c_automobile_design, sk_ic_engines, 'intermediate', 1.0);
    
    -- EV Engineer
    INSERT INTO career_skills (career_id, skill_id, required_level, weight) VALUES
    (c_ev_eng, sk_ev, 'intermediate', 2.0),
    (c_ev_eng, sk_circuit, 'intermediate', 1.0),
    (c_ev_eng, sk_matlab, 'beginner', 1.0);

    -- ==========================================
    -- 4. INSERT ASSESSMENTS (Student-Friendly Career Discovery Bank)
    -- ==========================================
    -- Q1: Logic (Broad Discovery - Multi-Domain Activity Exploration)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('Imagine your college gives you a free project and says: "Build or improve something useful." What would you most enjoy working on?', 'Logic', 'broad', 'software', 1) 
    RETURNING id INTO q1;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q1, '💻 Create something people can use on a phone or computer', '{"Software Developer": 3, "Frontend Developer": 3, "Full Stack Developer": 2}', '{"software": 10, "data_ai": 3, "cybersecurity": 2}'),
    (q1, '📊 Look at information and discover useful patterns to make decisions', '{"Data Analyst": 3, "Backend Developer": 2}', '{"data_ai": 10, "software": 4}'),
    (q1, '🛡️ Make a computer system safer and harder to misuse', '{"Cybersecurity Analyst": 3, "Backend Developer": 2}', '{"cybersecurity": 10, "software": 3}'),
    (q1, '⚡ Build something using sensors, wires, or electronic parts', '{"Embedded Systems Engineer": 3, "VLSI Design Engineer": 2, "Electrical Design Engineer": 2}', '{"electronics_embedded": 10, "electrical_energy": 6}'),
    (q1, '🏍️ Improve how a machine, vehicle, or physical product works', '{"Automobile Design Engineer": 3, "Mechanical Design Engineer": 3, "EV Engineer": 2}', '{"mechanical_design": 8, "automotive_ev": 8}'),
    (q1, '📐 Design or improve a building, space, or physical structure', '{"Structural Engineer": 3, "Site Engineer": 2}', '{"construction_infra": 10, "mechanical_design": 3}'),
    (q1, '🏭 Find a way to make a process faster or more automatic', '{"Manufacturing Engineer": 3, "HVAC Engineer": 1}', '{"manufacturing_automation": 10, "electrical_energy": 4}'),
    (q1, '🤷 I am not sure yet', '{}', '{}');

    -- Q2: Hardware (Broad Discovery - Team Solution)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('Imagine working on a team creating a smart hospital clinic. Which part of the solution would you find most interesting to work on?', 'Hardware', 'broad', 'electronics_embedded', 2) 
    RETURNING id INTO q2;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q2, '📱 Creating the patient appointment screens and mobile interface', '{"Frontend Developer": 3, "Full Stack Developer": 3, "Software Developer": 2}', '{"software": 10}'),
    (q2, '🖲️ Assembling the medical sensors that monitor heart rate and vitals', '{"Embedded Systems Engineer": 3, "VLSI Design Engineer": 3, "Electrical Design Engineer": 2}', '{"electronics_embedded": 10, "electrical_energy": 6}'),
    (q2, '🏥 Overseeing clinic building layout, air ventilation, and structural safety', '{"Site Engineer": 3, "Structural Engineer": 2, "HVAC Engineer": 2}', '{"construction_infra": 10, "mechanical_design": 5}'),
    (q2, '🔐 Setting up defenses to protect sensitive medical records from intruders', '{"Cybersecurity Analyst": 3, "Backend Developer": 2}', '{"cybersecurity": 10, "software": 4}'),
    (q2, '🤷 I am not sure yet', '{}', '{}');

    -- Q3: Environment (Broad Discovery - Work Environment)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('Where would you feel most energized and productive spending your workday?', 'Environment', 'broad', 'general', 3) 
    RETURNING id INTO q3;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q3, '🖥️ In a modern tech office or remote setup working with computer screens and digital tools', '{"Software Developer": 2, "Full Stack Developer": 2, "Data Analyst": 2, "Backend Developer": 2}', '{"software": 8, "data_ai": 8, "cybersecurity": 8}'),
    (q3, '🔬 In an experimental workshop testing circuit boards, sensor devices, and battery setups', '{"Embedded Systems Engineer": 3, "VLSI Design Engineer": 3, "Electrical Design Engineer": 2}', '{"electronics_embedded": 10, "electrical_energy": 6}'),
    (q3, '🦺 On an active project site or manufacturing floor seeing physical designs built into reality', '{"Site Engineer": 3, "Manufacturing Engineer": 3, "Structural Engineer": 2}', '{"construction_infra": 8, "manufacturing_automation": 8}'),
    (q3, '🎨 In a 3D modeling studio designing physical shapes and moving machine parts', '{"Mechanical Design Engineer": 3, "Automobile Design Engineer": 3}', '{"mechanical_design": 10, "automotive_ev": 6}'),
    (q3, '🤷 I am not sure yet', '{}', '{}');

    -- Q4: Analytics (Broad Discovery - Information & Logic)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When faced with an interesting collection of facts and numbers, what sounds most appealing to do?', 'Analytics', 'broad', 'data_ai', 4) 
    RETURNING id INTO q4;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q4, '📊 Finding hidden trends, calculating summaries, and turning numbers into visual charts', '{"Data Analyst": 3, "Backend Developer": 2}', '{"data_ai": 10, "software": 5}'),
    (q4, '📐 Calculating load limits, balance of forces, and safety factors for physical structures', '{"Structural Engineer": 3, "Mechanical Design Engineer": 2, "HVAC Engineer": 1}', '{"construction_infra": 8, "mechanical_design": 8}'),
    (q4, '🎨 Designing a beautiful, intuitive visual report that everyone loves to view', '{"Frontend Developer": 3, "Software Developer": 2}', '{"software": 8, "data_ai": 4}'),
    (q4, '🛡️ Checking records to identify suspicious patterns or unauthorized attempts', '{"Cybersecurity Analyst": 3, "Software Developer": 1}', '{"cybersecurity": 10, "software": 3}'),
    (q4, '🤷 I am not sure yet', '{}', '{}');

    -- Q5: Design (Broad Discovery - Mobility & Mechanism Curiosity)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When you look at an electric vehicle or modern machine, what makes you most curious?', 'Design', 'broad', 'mechanical_design', 5) 
    RETURNING id INTO q5;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q5, '🔋 How the battery pack and motor deliver smooth, quiet acceleration', '{"EV Engineer": 3, "Electrical Design Engineer": 2, "Automobile Design Engineer": 2}', '{"automotive_ev": 10, "electrical_energy": 8}'),
    (q5, '🏍️ How the aerodynamic frame, steering, and suspension handle rough bumps', '{"Automobile Design Engineer": 3, "Mechanical Design Engineer": 3}', '{"mechanical_design": 10, "automotive_ev": 8}'),
    (q5, '📱 How the digital dashboard screen syncs real-time information smoothly', '{"Software Developer": 2, "Embedded Systems Engineer": 2, "Cybersecurity Analyst": 1}', '{"software": 8, "electronics_embedded": 8}'),
    (q5, '🏭 How robotic assembly machines put every component together with high precision', '{"Manufacturing Engineer": 3, "Mechanical Design Engineer": 2}', '{"manufacturing_automation": 10, "mechanical_design": 5}'),
    (q5, '🤷 I am not sure yet', '{}', '{}');

    -- Q6: Civil (Deep Dive - Infrastructure & Construction)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('If you were helping build a new bridge or college campus, which role would you prefer?', 'Civil', 'deep_dive', 'construction_infra', 6) 
    RETURNING id INTO q6;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q6, '📐 Calculating the strength of concrete beams and earthquake-resistant foundations', '{"Structural Engineer": 3, "Site Engineer": 1}', '{"construction_infra": 10}'),
    (q6, '🦺 Being on-site directing workers, testing concrete batches, and checking safety', '{"Site Engineer": 3, "Structural Engineer": 1}', '{"construction_infra": 10}'),
    (q6, '💧 Designing drainage paths, water recycling systems, and environmental site grading', '{"Site Engineer": 2, "Structural Engineer": 2}', '{"construction_infra": 8}'),
    (q6, '🤷 I am not sure yet', '{}', '{}');

    -- Q7: Electrical (Deep Dive - Electrical & Energy Systems)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('Which electrical problem sounds most engaging for you to solve?', 'Electrical', 'deep_dive', 'electrical_energy', 7) 
    RETURNING id INTO q7;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q7, '⚡ Designing clean solar power wiring, energy distribution, and industrial motor panels', '{"Electrical Design Engineer": 3, "EV Engineer": 2}', '{"electrical_energy": 10}'),
    (q7, '🔬 Configuring industrial circuit breakers, power transformers, and backup generators', '{"Electrical Design Engineer": 3, "Manufacturing Engineer": 2}', '{"electrical_energy": 10, "manufacturing_automation": 4}'),
    (q7, '🔋 Improving battery charge speed, energy storage, and power efficiency', '{"EV Engineer": 3, "Electrical Design Engineer": 2}', '{"electrical_energy": 9, "automotive_ev": 8}'),
    (q7, '🤷 I am not sure yet', '{}', '{}');

    -- Q8: Automotive (Deep Dive - Automotive & Mobility)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When thinking about future transport, what sounds most exciting to build?', 'Automotive', 'deep_dive', 'automotive_ev', 8) 
    RETURNING id INTO q8;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q8, '⚡ High-voltage electric vehicle battery packs and regenerative motor drives', '{"EV Engineer": 3, "Electrical Design Engineer": 2}', '{"automotive_ev": 10, "electrical_energy": 6}'),
    (q8, '🏎️ High-performance car suspension, aerodynamic chassis, and crash safety structures', '{"Automobile Design Engineer": 3, "Mechanical Design Engineer": 2}', '{"automotive_ev": 10, "mechanical_design": 6}'),
    (q8, '🛡️ Smart driving sensors that detect lane markings and obstacles', '{"Embedded Systems Engineer": 2, "EV Engineer": 2, "Software Developer": 2}', '{"automotive_ev": 8, "electronics_embedded": 8}'),
    (q8, '🤷 I am not sure yet', '{}', '{}');

    -- Q9: Security (Deep Dive - Cybersecurity & Defense)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('How would you prefer to protect computer systems and digital information?', 'Security', 'deep_dive', 'cybersecurity', 9) 
    RETURNING id INTO q9;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q9, '🔐 Thinking like an ethical hacker to find security holes before bad actors do', '{"Cybersecurity Analyst": 3, "Software Developer": 1}', '{"cybersecurity": 10}'),
    (q9, '🛡️ Setting up automated defenses, secure servers, and firewall barriers', '{"Backend Developer": 3, "Full Stack Developer": 2, "Cybersecurity Analyst": 1}', '{"cybersecurity": 8, "software": 6}'),
    (q9, '🔍 Reviewing software code to make sure private user data can never be leaked', '{"Cybersecurity Analyst": 2, "Software Developer": 2, "Backend Developer": 2}', '{"cybersecurity": 9, "software": 7}'),
    (q9, '🤷 I am not sure yet', '{}', '{}');

    -- Q10: Mechanical (Deep Dive - Physical Systems & Machinery)
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When designing physical components, which activity gives you the greatest satisfaction?', 'Mechanical', 'deep_dive', 'mechanical_design', 10) 
    RETURNING id INTO q10;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q10, '⚙️ Crafting precision 3D CAD models of gears, brackets, and robotic parts', '{"Mechanical Design Engineer": 3, "Automobile Design Engineer": 2}', '{"mechanical_design": 10, "automotive_ev": 5}'),
    (q10, '🏭 Setting up automated factory assembly lines and testing physical quality', '{"Manufacturing Engineer": 3, "HVAC Engineer": 1}', '{"manufacturing_automation": 10}'),
    (q10, '❄️ Designing heating, ventilation, and air conditioning systems for large buildings', '{"HVAC Engineer": 3, "Mechanical Design Engineer": 2}', '{"mechanical_design": 8}'),
    (q10, '🤷 I am not sure yet', '{}', '{}');

    -- Q11: Software Deep Dive
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When creating a digital application, which part of the challenge sounds most enjoyable?', 'Logic', 'deep_dive', 'software', 11) 
    RETURNING id INTO q11;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q11, '🎨 Designing how the application looks, feels, and interacts smoothly with users', '{"Frontend Developer": 3, "Full Stack Developer": 2}', '{"software": 10}'),
    (q11, '⚙️ Building the core logic, databases, and communication rules running behind the scenes', '{"Backend Developer": 3, "Software Developer": 2}', '{"software": 10}'),
    (q11, '🌐 Connecting the visual screens and background servers into a complete working product', '{"Full Stack Developer": 3, "Software Developer": 2}', '{"software": 10}'),
    (q11, '🤷 I am not sure yet', '{}', '{}');

    -- Q12: Data & Analytics Deep Dive
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When exploring patterns in information, what type of project would you enjoy most?', 'Analytics', 'deep_dive', 'data_ai', 12) 
    RETURNING id INTO q12;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q12, '📊 Turning messy datasets into clear, interactive visual dashboards for decision makers', '{"Data Analyst": 3, "Frontend Developer": 1}', '{"data_ai": 10}'),
    (q12, '🤖 Building automated algorithms that learn from past examples to forecast future outcomes', '{"Data Analyst": 2, "Software Developer": 2, "Backend Developer": 2}', '{"data_ai": 10, "software": 5}'),
    (q12, '🗄️ Organizing data tables and query pipelines so large amounts of information load instantly', '{"Backend Developer": 3, "Data Analyst": 2}', '{"data_ai": 8, "software": 8}'),
    (q12, '🤷 I am not sure yet', '{}', '{}');

    -- Q13: Electronics & Embedded Deep Dive
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When working with electronic devices, which activity sounds most fascinating?', 'Hardware', 'deep_dive', 'electronics_embedded', 13) 
    RETURNING id INTO q13;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q13, '💻 Writing code that directly interacts with motors, LEDs, and robotic sensors', '{"Embedded Systems Engineer": 3, "Software Developer": 2}', '{"electronics_embedded": 10, "software": 4}'),
    (q13, '🔬 Designing microscopic circuit connections inside computer microchips', '{"VLSI Design Engineer": 3, "Embedded Systems Engineer": 1}', '{"electronics_embedded": 10}'),
    (q13, '⚡ Soldering and testing physical printed circuit boards with probes and meters', '{"Embedded Systems Engineer": 2, "Electrical Design Engineer": 2}', '{"electronics_embedded": 8, "electrical_energy": 6}'),
    (q13, '🤷 I am not sure yet', '{}', '{}');

    -- Q14: Universal Work Style
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When you work on a project, which way of working feels most natural and energizing to you?', 'Environment', 'work_style', 'work_style', 14) 
    RETURNING id INTO q14;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q14, '🤝 Collaborating closely with teammates in real-time, brainstorming and testing ideas together', '{"Full Stack Developer": 1, "Site Engineer": 1}', '{"work_style": 5}'),
    (q14, '🎯 Having clear individual ownership of a specific piece, diving into uninterrupted focus', '{"Software Developer": 1, "Data Analyst": 1, "VLSI Design Engineer": 1}', '{"work_style": 5}'),
    (q14, '🔨 Building rapid hands-on drafts and physical models to see what works immediately', '{"Embedded Systems Engineer": 1, "Mechanical Design Engineer": 1}', '{"work_style": 5}'),
    (q14, '🤷 I am not sure yet', '{}', '{}');

    -- Q15: Universal Problem Solving
    INSERT INTO assessment_questions (question_text, category, phase, domain, order_num) 
    VALUES ('When something you build does not work as expected, what is your first natural instinct?', 'Logic', 'problem_solving', 'problem_solving', 15) 
    RETURNING id INTO q15;
    INSERT INTO assessment_options (question_id, option_text, career_weight, domain_weight) VALUES
    (q15, '🔍 Tracing step-by-step through the process to isolate the exact point where it broke', '{"Backend Developer": 1, "Cybersecurity Analyst": 1}', '{"problem_solving": 5}'),
    (q15, '💡 Stepping back to look at the big picture and experimenting with a creative alternative', '{"Frontend Developer": 1, "Automobile Design Engineer": 1}', '{"problem_solving": 5}'),
    (q15, '🧪 Testing each individual component separately until the faulty piece is found', '{"Embedded Systems Engineer": 1, "Mechanical Design Engineer": 1}', '{"problem_solving": 5}'),
    (q15, '🤷 I am not sure yet', '{}', '{}');

    -- ==========================================
    -- 5. INSERT PROJECTS (Rich Diploma Projects)
    -- ==========================================
    INSERT INTO projects (title, description, difficulty, estimated_hours) VALUES 
    ('Personal Portfolio Website', 'Build a responsive portfolio using HTML, CSS, and JS.', 'beginner', 20) RETURNING id INTO p_web;
    INSERT INTO projects (title, description, difficulty, estimated_hours) VALUES 
    ('Weather API Integration', 'Fetch data from a public weather API using Python or Node.js.', 'intermediate', 15) RETURNING id INTO p_api;
    INSERT INTO projects (title, description, difficulty, estimated_hours) VALUES 
    ('3D Gear Assembly', 'Design a functional gear assembly in SolidWorks.', 'intermediate', 30) RETURNING id INTO p_cad;
    INSERT INTO projects (title, description, difficulty, estimated_hours) VALUES 
    ('Automated Plant Waterer', 'Use a microcontroller and sensors to water a plant.', 'intermediate', 25) RETURNING id INTO p_circuit;

    -- Map Projects to Careers
    INSERT INTO career_projects (career_id, project_id) VALUES
    (c_frontend, p_web),
    (c_fullstack, p_web),
    (c_backend, p_api),
    (c_sde, p_api),
    (c_data_analyst, p_api),
    (c_mech_design, p_cad),
    (c_automobile_design, p_cad),
    (c_manufacturing, p_cad),
    (c_embedded, p_circuit),
    (c_electrical_design, p_circuit),
    (c_ev_eng, p_circuit);

    -- Seed Interests
    INSERT INTO interests (name) VALUES
    ('Coding'), ('Web Design'), ('Data Science'), ('Cybersecurity'),
    ('Robotics'), ('Automobiles'), ('Renewable Energy'), ('Construction'),
    ('Hardware Design'), ('3D Modeling'), ('AI/ML');

END $$;
