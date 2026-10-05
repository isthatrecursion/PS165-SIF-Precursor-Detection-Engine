import json, random, base64
from pathlib import Path
from datetime import date, timedelta
random.seed(42)
SITES = {
    'Refinery': ['Digboi Refinery','Numaligarh Refinery Unit','Jorhat Refinery Complex','Guwahati Refinery'],
    'Gas Processing': ['Lakwa Gas Processing Plant','Sibasagar Gas Terminal','Moran Gas Compressor Station'],
    'Pipeline': ['Naharkatia Pipeline Station','Duliajan Pipeline Manifold','Rajgarh Booster Station','Makum Pump Station'],
    'EP': ['Geleki Oil Field','Hugrijan Well Pad','Barekuri Drilling Site','Ahomgaon Production Station'],
    'Marketing-POL': ['Noonmati POL Depot','Tengakhat Terminal'],
    'Marketing-LPG': ['Dibrugarh LPG Bottling Plant','Tinsukia LPG Storage'],
}
ALL_SITES = [(s,sec) for sec,sl in SITES.items() for s in sl]
EQUIPMENT = ['storage tank','compressor','pipeline valve','electrical panel','overhead crane','pressure vessel','heat exchanger','flare stack','centrifugal pump','portable gas detector','blowout preventer','wellhead assembly','three-phase separator','loading arm','steam boiler','distribution transformer','reciprocating compressor','control valve','piping manifold','pressure safety valve','chemical injection skid','scaffold structure','forklift','LPG filling carousel','motor control centre','gas turbine','fire water pump','hydrant system','instrument air compressor']
REPORTER_ROLES = ['Operator','Contractor Technician','Shift Supervisor','Safety Officer','Maintenance Technician','Drilling Engineer','Field Inspector','Process Engineer','Electrician','Rigger','Permit Issuer','Control Room Operator','Dispatch Supervisor','HSE Manager']
CAUSE_CATEGORIES = ['Violation of Work Permit System','Pilferage/miscreant activities','Inadequate hazard identification or risk assessment','Inadequate work standards/procedures/disregard of SOP','Inadequate competence','Inadequate supervision','Design deficiency','Noncompliance of Management of Change','Poor maintenance and Inspection','Negligent driving/Road/Crane/Hydra accidents','Inadequate/defective warning systems/safety devices','Non-compliance to PPE/fall and slip','Equipment failure','Others']
SHIFTS = ['Day','Night','General']
START_DATE = date(2023,1,1); END_DATE = date(2024,6,30)
DAYS_RANGE = (END_DATE - START_DATE).days
def rnd_date(): return (START_DATE + timedelta(days=random.randint(0,DAYS_RANGE))).isoformat()
def ri(*c): return random.choice(list(c))

CLEAR_POS = [
    lambda: dict(
        text=('Electrician started replacing faulty contactor on MCC panel '+ri('P-12','E-07','LV-03','E-14')+' without isolating electrical supply. No LOTO was applied and breaker was in ON position throughout the job. A live conductor was briefly touched causing a small arc flash. Shift supervisor was absent.'),
        energy=['electrical'], barrier_phrase='No LOTO was applied', barrier_status='absent',
        iogp=['Energy Isolation','Bypassing Safety Controls'], cause='Violation of Work Permit System',
        incident=ri('Hi-Po Near Miss','Near Miss'), hi_po=True),
    lambda: dict(
        text=('Contractor team opened a flanged joint on the '+ri('HP gas','high-pressure condensate','fuel gas','instrument air')+' line without a valid work permit. Line was at '+ri('42','18','55','34')+' kg/cm2 and had not been depressurized. Gas was released at the joint. Area evacuated by shift supervisor.'),
        energy=['pressure'], barrier_phrase='without a valid work permit', barrier_status='absent',
        iogp=['Energy Isolation','Hot Work'], cause='Violation of Work Permit System',
        incident=ri('Near Miss','Hi-Po Near Miss'), hi_po=True),
    lambda: dict(
        text=('Worker entered the '+ri('crude oil storage tank','slop tank','effluent sump','underground drain pit')+' for internal inspection without gas testing the atmosphere first. No standby man was posted. O2 level measured at '+ri('14.2','13.8','15.1')+'% -- below safe threshold. Entry permit had not been raised.'),
        energy=['confined_space','H2S'], barrier_phrase='without gas testing the atmosphere first', barrier_status='absent',
        iogp=['Confined Space'], cause='Violation of Work Permit System',
        incident=ri('Hi-Po Near Miss','Near Miss'), hi_po=True),
    lambda: dict(
        text=('Grinding work on a '+ri('structural beam','vessel nozzle','pipe flange','drain connection')+' was ongoing in the '+ri('tank farm area','compressor bay','pump house','process unit')+' without a designated fire watch person. Hot work permit found expired by '+ri('one','two')+' day(s). Work was continuing regardless. No fire suppression equipment staged nearby.'),
        energy=['thermal'], barrier_phrase='without a designated fire watch person', barrier_status='absent',
        iogp=['Hot Work'], cause='Violation of Work Permit System',
        incident=ri('Unsafe Act','Near Miss'), hi_po=False),
    lambda: dict(
        text=('Contractor technician observed working at '+ri('6.5','8','11','7','9')+' metres on scaffold without a fall-arrest harness. No lifeline had been rigged. Scaffold lacked a top guardrail. Task: '+ri('replacing pipe insulation','painting the structural column','installing cable trays')+'.'),
        energy=['fall_gravity'], barrier_phrase='without a fall-arrest harness', barrier_status='absent',
        iogp=['Working at Height'], cause='Non-compliance to PPE/fall and slip',
        incident=ri('Unsafe Act','Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('During start-up of '+ri('compressor K-201','pump P-305','boiler B-102','turbine GT-01')+', the '+ri('high-high pressure trip','low-low level trip','high temperature trip')+' interlock was found bypassed using a manual jumper. No bypass register entry existed. Equipment had been running in this state for '+ri('3','6','8')+' hours without authorisation.'),
        energy=['pressure','mechanical'], barrier_phrase='interlock was found bypassed using a manual jumper', barrier_status='bypassed',
        iogp=['Bypassing Safety Controls','Energy Isolation'], cause='Noncompliance of Management of Change',
        incident=ri('Unsafe Condition','Hi-Po Near Miss'), hi_po=True),
    lambda: dict(
        text=('Two operators entered the '+ri('well cellar','drain pit','separator skid area','pig receiver area')+' without checking H2S levels. The area H2S detector had been offline due to a sensor fault unreported for '+ri('2','4','5','3')+' days. One operator felt dizziness and was evacuated. H2S subsequently measured at '+ri('18','22','31')+' ppm.'),
        energy=['H2S'], barrier_phrase='H2S detector had been offline', barrier_status='failed',
        iogp=['Confined Space','Energy Isolation'], cause='Inadequate/defective warning systems/safety devices',
        incident=ri('Minor Incident','Hi-Po Near Miss'), hi_po=True),
    lambda: dict(
        text=('A '+ri('4.5','6','8','12')+' tonne '+ri('pressure vessel section','heat exchanger bundle','pump casing','motor unit')+' was lifted without a written lift plan. SWL tag on crane was '+ri('missing','illegible','expired')+'. No exclusion zone established. '+ri('Two','Three')+' workers remained in the swing radius during the lift.'),
        energy=['fall_gravity','mechanical'], barrier_phrase='without a written lift plan', barrier_status='absent',
        iogp=['Safe Mechanical Lifting','Line of Fire'], cause='Inadequate hazard identification or risk assessment',
        incident=ri('Unsafe Condition','Near Miss'), hi_po=True),
    lambda: dict(
        text=('Fuel gas detected leaking at flanged connection on line FG-'+ri('204','118','307','415')+' adjacent to a hot surface at approximately '+ri('310','280','350','420')+' deg C. Gas test was not performed before maintenance access. Upstream isolation valve had not been closed. Area is classified Zone-1 hazardous.'),
        energy=['thermal','chemical','pressure'], barrier_phrase='Gas test was not performed before maintenance access', barrier_status='absent',
        iogp=['Hot Work','Energy Isolation'], cause='Inadequate hazard identification or risk assessment',
        incident=ri('Near Miss','Hi-Po Near Miss'), hi_po=True),
    lambda: dict(
        text=('At well pad '+ri('GK-07','HR-14','BR-02','AG-11')+', the BOP was not function-tested before commencing the '+ri('production casing','intermediate casing')+' run. A kick was detected at formation depth. BOP activated but crew response was delayed as procedure had not been covered in the pre-job briefing.'),
        energy=['BOP','pressure'], barrier_phrase='BOP was not function-tested', barrier_status='failed',
        iogp=['Energy Isolation'], cause='Inadequate work standards/procedures/disregard of SOP',
        incident=ri('Hi-Po Near Miss','Major Incident'), hi_po=True),
    lambda: dict(
        text=('Maintenance crew performing '+ri('cold cutting','drilling','grinding')+' inside LPG filling area without a cold work permit. Filling carousel was not stopped; cylinders continued to be filled during the task. No gas test performed in the immediate work area.'),
        energy=['pressure','chemical'], barrier_phrase='without a cold work permit', barrier_status='absent',
        iogp=['Hot Work','Energy Isolation'], cause='Violation of Work Permit System',
        incident=ri('Unsafe Act','Near Miss'), hi_po=True),
    lambda: dict(
        text=('Scaffold at Unit-'+ri('3','5','7','9')+' found partially collapsed at '+ri('4','6','8')+'-metre level. Base plates resting on loose soil without mud sills. No scaffold inspection tag was affixed. Workers from previous shift had been using it throughout.'),
        energy=['fall_gravity'], barrier_phrase='No scaffold inspection tag was affixed', barrier_status='absent',
        iogp=['Working at Height'], cause='Poor maintenance and Inspection',
        incident=ri('Unsafe Condition','Near Miss'), hi_po=False),
    lambda: dict(
        text=('found drain valve on HP separator left open during walkthrough. isolation not confirmed before opening. '+ri('pressurized','live gas present','still under pressure')+' at outlet. informed shift i/c. PTW was not issued for this work.'),
        energy=['pressure'], barrier_phrase='isolation not confirmed before opening', barrier_status='absent',
        iogp=['Energy Isolation'], cause='Violation of Work Permit System',
        incident=ri('Near Miss','Unsafe Act'), hi_po=False),
    lambda: dict(
        text=('tank truck at '+ri('POL gantry','LPG loading bay','bitumen loading arm','MS product gantry')+' not earthed before product loading commenced. earthing cable missing from connection point. driver had started '+ri('pumping','loading','product transfer')+' when discovered.'),
        energy=['electrical','chemical'], barrier_phrase='not earthed before product loading commenced', barrier_status='absent',
        iogp=['Energy Isolation'], cause='Inadequate work standards/procedures/disregard of SOP',
        incident=ri('Unsafe Act','Near Miss'), hi_po=False),
    lambda: dict(
        text=('Excavation work found ongoing near the '+ri('buried crude oil line','underground gas distribution pipe','subterranean process drain')+' at Unit-'+ri('2','4','6')+'. Excavation permit had expired '+ri('two','three')+' days prior. No cable or pipe detection equipment was used before digging began.'),
        energy=['pressure','chemical'], barrier_phrase='Excavation permit had expired', barrier_status='failed',
        iogp=['Energy Isolation','Line of Fire'], cause='Violation of Work Permit System',
        incident=ri('Unsafe Act','Near Miss'), hi_po=True),
    lambda: dict(
        text=('Welding on a '+ri('pipe spool','vessel nozzle','structural bracket')+' in the '+ri('tank farm bund','gas compression area','fuel oil pump house')+'. Initial gas test done in morning but when work resumed after lunch, no repeat gas test was carried out as required by the hot work permit. Gas concentration not confirmed safe before re-igniting the arc.'),
        energy=['thermal','chemical'], barrier_phrase='no repeat gas test was carried out', barrier_status='absent',
        iogp=['Hot Work'], cause='Inadequate work standards/procedures/disregard of SOP',
        incident=ri('Unsafe Act','Near Miss'), hi_po=False),
    lambda: dict(
        text=('During maintenance on '+ri('compressor K-101','pump P-208','agitator M-04')+', the LOTO tag was removed and power restored while the technician was still inside the machine guard completing final checks. Technician had not formally returned isolation to the permit issuer. Machine was re-energised with person in danger zone.'),
        energy=['mechanical','electrical'], barrier_phrase='LOTO tag was removed while the technician was still inside the machine guard', barrier_status='failed',
        iogp=['Energy Isolation'], cause='Inadequate work standards/procedures/disregard of SOP',
        incident=ri('Hi-Po Near Miss','Near Miss'), hi_po=True),
    lambda: dict(
        text=('Hydrostatic test of pipeline spool at '+ri('85','120','95')+' bar was underway. Test boundary exclusion zone had been defined but was not enforced -- two operators entered to inspect a flange while pressure was still applied. Test supervisor did not stop work.'),
        energy=['pressure'], barrier_phrase='exclusion zone had been defined but was not enforced', barrier_status='failed',
        iogp=['Line of Fire','Energy Isolation'], cause='Inadequate supervision',
        incident=ri('Unsafe Act','Near Miss'), hi_po=True),
    lambda: dict(
        text=('While replacing the diaphragm on chemical injection pump CI-'+ri('04','07','11')+', the upstream chemical isolation valve was found to be passing. Technician assumed the closed position was effective without downstream pressure verification. Chemical was released when housing was opened.'),
        energy=['chemical','pressure'], barrier_phrase='isolation valve was found to be passing', barrier_status='failed',
        iogp=['Energy Isolation'], cause='Inadequate hazard identification or risk assessment',
        incident=ri('Minor Incident','Near Miss'), hi_po=False),
    lambda: dict(
        text=('Housekeeping in progress at Unit-'+ri('3','5')+' while a high-pressure flush was running on an adjacent system at '+ri('60','80','45')+' bar. No SIMOPS assessment had been carried out and no coordination meeting was held. Workers from one crew were unaware of the adjacent high-pressure activity.'),
        energy=['pressure','SIMOPS'], barrier_phrase='No SIMOPS assessment had been carried out', barrier_status='absent',
        iogp=['SIMOPS','Line of Fire'], cause='Inadequate hazard identification or risk assessment',
        incident=ri('Unsafe Condition','Hi-Po Near Miss'), hi_po=True),
    lambda: dict(
        text=('ESD valve on wellhead '+ri('WH-03','WH-07','WH-12')+' found manually bypassed using a cable tie on the solenoid pilot. Well producing at '+ri('280','350','420')+' psi. No bypass authorisation on file. Bypass in place since previous maintenance -- reason unknown.'),
        energy=['pressure','BOP'], barrier_phrase='ESD valve found manually bypassed', barrier_status='bypassed',
        iogp=['Bypassing Safety Controls','Energy Isolation'], cause='Noncompliance of Management of Change',
        incident=ri('Unsafe Condition','Hi-Po Near Miss'), hi_po=True),
    lambda: dict(
        text=('Quarterly inspection found PSV on vessel V-'+ri('115','208','301')+' isolated with block valve in closed position. No live MOC or work order associated with this isolation. Vessel had been operating without relief protection for estimated '+ri('3','5','8')+' weeks.'),
        energy=['pressure'], barrier_phrase='PSV had been isolated with block valve in closed position', barrier_status='bypassed',
        iogp=['Bypassing Safety Controls','Energy Isolation'], cause='Noncompliance of Management of Change',
        incident=ri('Unsafe Condition','Hi-Po Near Miss'), hi_po=True),
    lambda: dict(
        text=('Worker fell approximately '+ri('3','4.5','5')+' metres from scaffold when anchor point failed near the '+ri('overhead pipe rack','storage tank top','column instrument platform')+'. Post-incident inspection found anchor bolt had not been verified during scaffold sign-off. Worker sustained '+ri('a fractured wrist','rib injuries','soft tissue injuries')+'.'),
        energy=['fall_gravity'], barrier_phrase='anchor bolt had not been verified during scaffold sign-off', barrier_status='failed',
        iogp=['Working at Height'], cause='Poor maintenance and Inspection',
        incident=ri('Minor Incident','Major Incident'), hi_po=False),
    lambda: dict(
        text=('Company vehicle transporting '+ri('maintenance crew','contractor personnel','survey team')+' to '+ri('the well site','the remote pumping station')+' was involved in a rollover on the '+ri('field access road','dirt approach track')+'. No journey management plan had been submitted. Driver not in contact with control room. Tyre marks indicate excessive speed.'),
        energy=['mechanical'], barrier_phrase='No journey management plan had been submitted', barrier_status='absent',
        iogp=['Driving'], cause='Negligent driving/Road/Crane/Hydra accidents',
        incident=ri('Minor Incident','Major Incident'), hi_po=True),
    lambda: dict(
        text=('Unit '+ri('3','5','7')+' mein aaj gas leakage dekha flanged joint pe. PTW nahi tha aur isolation bhi nahi ki gayi. Shift incharge ko bataya, area evacuate kiya gaya.'),
        energy=['pressure','chemical'], barrier_phrase='PTW nahi tha', barrier_status='absent',
        iogp=['Energy Isolation','Hot Work'], cause='Violation of Work Permit System',
        incident=ri('Near Miss','Hi-Po Near Miss'), hi_po=True, language_note='Hindi code-mix'),
    lambda: dict(
        text=('During transfer of '+ri('caustic soda solution','sulphuric acid','amine solution')+' via flexible hose, the hose burst at a crimped connection. Pre-job hose inspection had not been performed; the hose was past its replacement date by '+ri('4','6','3')+' months. Chemical splashed onto operator forearm. Minor burn through glove seam.'),
        energy=['chemical'], barrier_phrase='Pre-job hose inspection had not been performed', barrier_status='absent',
        iogp=['Energy Isolation'], cause='Poor maintenance and Inspection',
        incident=ri('Minor Incident','Near Miss'), hi_po=False),
    lambda: dict(
        text=('Electrical junction box JB-'+ri('204','117','309')+' found with door open and latches broken during evening rounds. Box contains live '+ri('415V','230V')+' terminals in outdoor location exposed to light rain. No tagging or barrier around the open box. Previous inspection had noted broken latches but corrective action was not completed.'),
        energy=['electrical'], barrier_phrase='corrective action was not completed', barrier_status='failed',
        iogp=['Energy Isolation'], cause='Poor maintenance and Inspection',
        incident=ri('Unsafe Condition','Near Miss'), hi_po=False),
    lambda: dict(
        text=('Maintenance team broke the flange on '+ri('product line PL-114','crude transfer line CL-07','gas condensate line GC-22')+' for a valve replacement. Double-block-and-bleed isolation was performed but the required blind was not inserted before opening the flange. Residual product drained at the joint.'),
        energy=['pressure','chemical'], barrier_phrase='the required blind was not inserted', barrier_status='absent',
        iogp=['Energy Isolation'], cause='Inadequate work standards/procedures/disregard of SOP',
        incident=ri('Near Miss','Unsafe Act'), hi_po=False),
]

HARD_POS = [
    lambda: dict(
        text=('Routine preventive maintenance on '+ri('pump P-112','compressor K-204','motor M-08','fan F-203')+' completed today. Technician noted that the isolation certificate had not been formally signed off before work started, but the job finished without incident. Equipment returned to service.'),
        energy=['electrical','mechanical'], barrier_phrase='isolation certificate had not been formally signed off', barrier_status='absent',
        iogp=['Energy Isolation'], cause='Violation of Work Permit System', incident=ri('Unsafe Act'), hi_po=False),
    lambda: dict(
        text=('Control room operator noted that the '+ri('low-flow trip','high-temperature alarm','low-level trip')+' on '+ri('cooling water pump P-307','seal oil pump P-214','feed pump P-101')+' had been disabled during last night shift to avoid nuisance tripping. System is otherwise operating normally at this time.'),
        energy=['mechanical','pressure'], barrier_phrase='had been disabled during last night shift', barrier_status='bypassed',
        iogp=['Bypassing Safety Controls'], cause='Noncompliance of Management of Change', incident=ri('Unsafe Condition'), hi_po=True),
    lambda: dict(
        text=('Workers were doing housekeeping in the '+ri('separator area','compressor shed','bund area')+' this afternoon. It was noted separately that a pressure test was ongoing on adjacent piping at '+ri('48','72','95')+' bar. No SIMOPS assessment was on record for the two concurrent activities.'),
        energy=['pressure','SIMOPS'], barrier_phrase='No SIMOPS assessment was on record', barrier_status='absent',
        iogp=['SIMOPS','Line of Fire'], cause='Inadequate hazard identification or risk assessment', incident=ri('Unsafe Condition'), hi_po=True),
    lambda: dict(
        text=('Quarterly inspection of the relief valve network completed. It was noted in passing that the PSV on '+ri('vessel V-115','drum D-208','tower T-301')+' had been isolated with a block valve closed '+ri('4','6','8')+' months ago for a temporary repair that was never completed. No active MOC exists.'),
        energy=['pressure'], barrier_phrase='PSV had been isolated with a block valve closed', barrier_status='bypassed',
        iogp=['Bypassing Safety Controls','Energy Isolation'], cause='Noncompliance of Management of Change', incident=ri('Unsafe Condition'), hi_po=True),
    lambda: dict(
        text=('Operations proceeded normally throughout the day shift. At end of shift the portable gas detector used by the '+ri('well site','separator area','pump station')+' crew was found to have a flat battery -- it had not been functioning for most of the shift. Work in the H2S-risk area continued throughout.'),
        energy=['H2S'], barrier_phrase='had not been functioning for most of the shift', barrier_status='failed',
        iogp=['Confined Space'], cause='Poor maintenance and Inspection', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('A permit to work for hot work on '+ri('the heat exchanger','the separator shell','the condensate line')+' was cancelled partway through the job due to a shift change. Isolations were not reinstated and the job site was left with a partly dismantled flange with no cap or blind. PTW closure procedure was not completed.'),
        energy=['thermal','pressure'], barrier_phrase='Isolations were not reinstated', barrier_status='failed',
        iogp=['Hot Work','Energy Isolation'], cause='Inadequate work standards/procedures/disregard of SOP', incident=ri('Unsafe Condition','Near Miss'), hi_po=False),
    lambda: dict(
        text=('During records review for '+ri('vessel V-201','reactor R-04','drum D-115')+', it was found that the last calibration record for the pressure relief valve was dated '+ri('3','4','5')+' years ago -- beyond the required inspection interval. No work order exists for re-calibration. Vessel operating at normal pressure.'),
        energy=['pressure'], barrier_phrase='beyond the required inspection interval', barrier_status='failed',
        iogp=['Energy Isolation'], cause='Poor maintenance and Inspection', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Shift changeover completed normally. Outgoing operator mentioned verbally to the incoming operator that the vent valve on the HP discharge line '+ri('had been left open during depressurisation','was stuck in the open position','could not be fully closed')+'. No formal log entry was made. Line pressure at handover: '+ri('38','54','67')+' kg/cm2.'),
        energy=['pressure'], barrier_phrase='No formal log entry was made', barrier_status='failed',
        iogp=['Energy Isolation'], cause='Inadequate work standards/procedures/disregard of SOP', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Equipment delivery at the '+ri('workshop','laydown area')+' today. During unloading of a '+ri('valve assembly','pump casing','heat exchanger shell')+', a contractor helper was observed standing directly below the suspended load while slings were being attached. Lift proceeded and load passed over the helper without contact.'),
        energy=['fall_gravity','mechanical'], barrier_phrase='standing directly below the suspended load', barrier_status='absent',
        iogp=['Safe Mechanical Lifting','Line of Fire'], cause='Inadequate supervision', incident=ri('Near Miss'), hi_po=False),
    lambda: dict(
        text=('Aaj subah ka kaam tha '+ri('electrical panel ka maintenance','pump P-108 ka overhaul','motor M-06 ka inspection')+'. Technician ne kaam shuru kiya bina isolation ke -- bola ki kaam chota hai toh permit ki zaroorat nahi. Koi LOTO nahi lagaya gaya tha.'),
        energy=['electrical'], barrier_phrase='bina isolation ke', barrier_status='absent',
        iogp=['Energy Isolation'], cause='Inadequate work standards/procedures/disregard of SOP', incident=ri('Unsafe Act'), hi_po=False, language_note='Hindi code-mix'),
    lambda: dict(
        text=('High-pressure alarm on '+ri('vessel V-204','drum D-115','separator S-03')+' was acknowledged by the control room operator during the night shift. No field verification or corrective action was taken for approximately '+ri('25','40','55')+' minutes. Alarm recurred twice before the high-high trip activated and shutdown occurred.'),
        energy=['pressure'], barrier_phrase='No field verification or corrective action was taken', barrier_status='failed',
        iogp=['Bypassing Safety Controls'], cause='Inadequate supervision', incident=ri('Unsafe Condition','Near Miss'), hi_po=False),
    lambda: dict(
        text=('Scaffold at Unit-'+ri('2','4','6')+' was found being used by '+ri('two','three')+' workers this morning before the scaffold inspection tag had been issued. Inspector had not yet completed sign-off. Workers were unaware of the tag requirement.'),
        energy=['fall_gravity'], barrier_phrase='before the scaffold inspection tag had been issued', barrier_status='absent',
        iogp=['Working at Height'], cause='Inadequate competence', incident=ri('Unsafe Act'), hi_po=False),
    lambda: dict(
        text=('Follow-up audit on corrective actions from the '+ri('Q1','Q2','Q3')+' safety review found that replacement of the failed gas detector in the '+ri('compressor building','well cellar','separator area')+' had not been completed. Action had been deferred twice. Detector remains non-functional.'),
        energy=['H2S','chemical'], barrier_phrase='replacement of the failed gas detector had not been completed', barrier_status='failed',
        iogp=['Confined Space'], cause='Poor maintenance and Inspection', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Confined space entry for cleaning of '+ri('tank T-07','vessel V-112','separator S-03')+' was carried out with a pre-entry gas test. Post-entry it was discovered that the gas detector used was overdue for calibration by '+ri('2','3','4')+' months. Readings from the uncalibrated instrument cannot be relied upon.'),
        energy=['confined_space','H2S','chemical'], barrier_phrase='gas detector was overdue for calibration', barrier_status='failed',
        iogp=['Confined Space'], cause='Poor maintenance and Inspection', incident=ri('Unsafe Condition','Near Miss'), hi_po=False),
    lambda: dict(
        text=('Maintenance team completed isolation of the '+ri('HSD storage line','naphtha feed line','crude header')+' before a planned tank entry. On verification, the position indicator on isolation valve XV-'+ri('204','118','307')+' showed closed but the valve body was found to be passing fluid. Discovery prevented tank entry.'),
        energy=['chemical','confined_space'], barrier_phrase='valve body was found to be passing fluid', barrier_status='failed',
        iogp=['Energy Isolation','Confined Space'], cause='Inadequate work standards/procedures/disregard of SOP', incident=ri('Near Miss'), hi_po=True),
    lambda: dict(
        text=('Post-test inspection completed for pipeline spool. All readings satisfactory. Crew closed out the PTW and returned line to service. The following morning a no-flow alarm indicated the test blind had not been removed before isolation valves were reopened. Line now pressurised with blind in place.'),
        energy=['pressure'], barrier_phrase='test blind had not been removed', barrier_status='failed',
        iogp=['Energy Isolation'], cause='Inadequate work standards/procedures/disregard of SOP', incident=ri('Near Miss','Unsafe Condition'), hi_po=False),
]

CLEAR_NEG = [
    lambda: dict(text='Routine housekeeping inspection in the '+ri('control room','workshop','storage area','canteen')+'. All areas found in good condition. No unsafe conditions. Records updated.', incident='Unsafe Condition'),
    lambda: dict(text='Pre-shift safety toolbox talk for '+ri('day shift','night shift','contractor')+' personnel. Topics: PPE usage, slips and trips, emergency muster. Attendance: '+str(random.randint(8,25))+' persons.', incident='Unsafe Condition'),
    lambda: dict(text='Minor '+ri('lubricant spill','water puddle','drip from drain')+' found near '+ri('pump P-105','filter skid','compressor drain')+'. Cleaned immediately. No injury or process impact. Cause: '+ri('worn gasket','loose fitting','sampling overflow')+'.', incident='Minor Incident'),
    lambda: dict(text='Safety officer observed a worker not wearing safety glasses in the '+ri('workshop','laydown area','storage room')+'. Worker spoken to. Glasses worn immediately. No injury. Toolbox reminder issued.', incident='Unsafe Act'),
    lambda: dict(text='Contractor safety induction completed for '+str(random.randint(3,12))+' new workers. All signed induction register and received site PPE.', incident='Unsafe Condition'),
    lambda: dict(text='Monthly fire extinguisher inspection done. '+str(random.randint(2,5))+' extinguishers with expired tags replaced. All others in good working order.', incident='Unsafe Condition'),
    lambda: dict(text='Vehicle found parked in no-parking zone near the '+ri('truck bay','security gate','warehouse entrance')+'. Driver asked to repark. No safety risk.', incident='Unsafe Condition'),
    lambda: dict(text='Operator observed leaving control room without signing the logbook. Reminded of the requirement. No process abnormality during that period.', incident='Unsafe Act'),
    lambda: dict(text='Eyewash station in the '+ri('chemical storage area','laboratory','battery room')+' checked -- water supply adequate, nozzles clean, station operational.', incident='Unsafe Condition'),
    lambda: dict(text='Noise survey in the '+ri('compressor building','pump house','turbine hall')+' recorded '+str(random.randint(82,91))+'-'+str(random.randint(92,105))+' dB(A). Hearing protection zone signage updated.', incident='Unsafe Condition'),
    lambda: dict(text='Pipe fitting work in the workshop completed with proper PTW, full PPE, and energy isolation in place. No anomaly. Work closed out.', incident='Unsafe Act'),
    lambda: dict(text='LT panel electrical maintenance completed. All isolation, LOTO, and permit conditions followed. Panel restored to service after testing.', incident='Unsafe Act'),
    lambda: dict(text='Vibration readings on '+ri('compressor K-301','pump P-207','fan F-104')+' taken during monitoring round -- within acceptable limits. Next reading in 30 days.', incident='Unsafe Condition'),
    lambda: dict(text='Scaffolding at Unit-'+ri('2','4','6')+' erected for turnaround work. Inspector has tagged and signed off all levels. Workers briefed on load limits.', incident='Unsafe Condition'),
    lambda: dict(text='Gate vehicle check: contractor truck had low tyre pressure on rear left. Tyre inflated before entry. Driver reminded of pre-trip inspection requirement.', incident='Unsafe Act'),
    lambda: dict(text='Aaj ki shift mein sab theek raha. Koi incident nahi hua. Sabne apna kaam sahi se kiya. Toolbox talk bhi complete hui. Log book updated.', incident='Unsafe Condition', language_note='Hindi code-mix'),
    lambda: dict(text='Storage yard monthly inspection done. Materials properly stacked and labelled. Passageways clear. No hazards identified.', incident='Unsafe Condition'),
    lambda: dict(text='Confined space permit records spot-checked for current month. All permits complete with gas test records, standby man entries, and signatures. No discrepancies.', incident='Unsafe Condition'),
    lambda: dict(text='Loading operations at the '+ri('product gantry','truck bay')+' -- earthing cables in place, loading arm secured before product transfer. No anomaly.', incident='Unsafe Act'),
    lambda: dict(text=ri('Daily','Weekly','Monthly')+' inspection of '+ri('first aid box','fire hose reel','emergency shower')+' in process area -- items stocked and functional. Log signed.', incident='Unsafe Condition'),
    lambda: dict(text='Containment bund at tank farm inspected. Bund walls intact, drain valve locked closed, sump clear. No ponding.', incident='Unsafe Condition'),
    lambda: dict(text='Emergency response drill at the '+ri('refinery','gas plant','pipeline station')+'. All personnel mustered within target time. Debrief completed. Minor improvement: signage repaint required.', incident='Unsafe Condition'),
    lambda: dict(text='Portable ladder inspection in process area. '+str(random.randint(1,3))+' ladders with oil or paint on rungs removed from service. All others cleared for use.', incident='Unsafe Condition'),
    lambda: dict(text='Management safety walk in the '+ri('CDU area','LPG bottling hall','compressor complex')+'. Permit boards current, PPE compliance observed, no concerns raised.', incident='Unsafe Condition'),
    lambda: dict(text='Chemical sampling at the '+ri('cooling tower','DM plant','process water system')+' using proper PPE including gloves and face shield. Sample dispatched to lab. No issues.', incident='Unsafe Act'),
    lambda: dict(text='Journey management call completed for field crew heading to remote well site. Departure, route, and ETA logged. Check-in confirmed at destination.', incident='Unsafe Act'),
    lambda: dict(text='Crane operator annual medical examination and competency assessment completed. Operator found fit. Certificate updated in records.', incident='Unsafe Condition'),
    lambda: dict(text='LOTO drill for '+ri('operations','maintenance')+' crew on '+ri('pump P-206','compressor K-103')+'. Steps completed correctly in '+str(random.randint(4,9))+' minutes. No deviation.', incident='Unsafe Condition'),
    lambda: dict(text='Safety culture survey distributed to all site personnel. Responses due within one week. Participation rate last quarter was '+str(random.randint(78,95))+'%. Results to be reviewed at next HSE meeting.', incident='Unsafe Condition'),
    lambda: dict(text='Routine check of personal gas monitors before shift start. All monitors charged and bump-tested. '+str(random.randint(0,2))+' monitors returned for battery replacement. Replacements issued.', incident='Unsafe Condition'),
]

HARD_NEG = [
    lambda: dict(
        text=('A small fire was reported in the '+ri('instrument room','electrical room','motor terminal box')+' at Unit-'+ri('3','5','7')+'. Extinguished by local CO2 extinguisher within '+ri('30 seconds','1 minute','90 seconds')+' by the on-duty operator. Electrical supply isolated before firefighting began. Fire watch maintained for '+ri('30','60')+' minutes. Investigation underway.'),
        energy=['electrical'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Equipment failure', incident=ri('Minor Incident','Near Miss'), hi_po=False),
    lambda: dict(
        text=('Gas cloud detected by fixed detector at Unit-'+ri('2','4','6')+' during the night shift. Emergency response immediately activated: area evacuated, isolation closed, source identified as a failed gasket. Gasket replaced under a valid hot work permit after gas test confirmed clear. Area declared safe.'),
        energy=['chemical','pressure'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Equipment failure', incident=ri('Near Miss','Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Critical overhead lift of a heat exchanger shell weighing '+str(random.randint(8,20))+' tonnes at the '+ri('refinery','gas plant','workshop')+'. All lift plan requirements satisfied: rigging certified, exclusion zone enforced, banksman present, inspector on site. Lift completed safely.'),
        energy=['fall_gravity','mechanical'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Safety officer presented three anonymised fatality case studies to the shift crew covering energy isolation failures from industry incidents. Discussion focused on PTW and LOTO learnings. Attendance: '+str(random.randint(10,20))+' persons.'),
        energy=[], barrier_phrase=None, barrier_status='n/a', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Confined space entry into the '+ri('slop tank','underground drain sump','separator vessel')+' completed. Gas test confirmed O2 20.9%, LEL 0%, H2S 0 ppm. Standby man present, rescue equipment staged. Continuous monitoring throughout. Workers exited safely.'),
        energy=['confined_space'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Hydrostatic pressure test of newly installed pipeline spool at '+ri('48','72','95')+' bar completed. Test blinds installed, pressure recorder certified, exclusion zone enforced throughout. No leaks detected. Test report signed and archived.'),
        energy=['pressure'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Explosion-proof luminaire in the '+ri('compressor house','pump skid area','wellhead shelter')+' found with cracked globe. Immediately de-energised and tagged out. Replacement ordered. Area adequately lit by adjacent luminaires. No uncontrolled energy source.'),
        energy=[], barrier_phrase=None, barrier_status='n/a', iogp=[], cause='Equipment failure', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('H2S alarm activated at '+ri('Geleki Oil Field','Ahomgaon Production Station')+' during day shift. All personnel donned SCBA within '+ri('45','60','75')+' seconds and mustered at assembly point. Area confirmed H2S-free after ventilation. Drill performance logged.'),
        energy=['H2S'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Safety walk flagged that if the relief valve on vessel V-'+ri('201','305','118')+' malfunctioned, an overpressure event could result. Inspection confirmed the valve is within calibration period and seat-tested satisfactorily. No further action required.'),
        energy=['pressure'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Aaj plant mein ek badi awaaz aayi -- sabko laga kuch serious hua. But it was just a steam hammer in the condensate line. Operator ne turant check kiya: line pressure normal thi, koi leak nahi. Shift supervisor ne bhi confirm kiya.'),
        energy=[], barrier_phrase=None, barrier_status='n/a', iogp=[], cause='Others', incident=ri('Near Miss'), hi_po=False, language_note='Hindi code-mix'),
    lambda: dict(
        text=('Contractor reported a near miss where a grinding wheel disc broke during use. Worker was wearing full face shield and machine guard was in place. Disc fragments contained by the guard. No injury. Equipment inspected and wheel type reviewed.'),
        energy=['mechanical'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Equipment failure', incident=ri('Near Miss'), hi_po=False),
    lambda: dict(
        text=('Simulated fire scenario at the '+ri('LPG bottling plant','refinery tank farm')+' as part of the annual emergency exercise. Fire brigade response time: '+str(random.randint(3,8))+' minutes. First aid team on standby. Debrief completed with observations for improvement.'),
        energy=[], barrier_phrase=None, barrier_status='n/a', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Pressure transmitter PT-'+ri('214','307','508')+' spiked to '+ri('98','115','87')+' bar triggering a high-pressure alarm. Field check confirmed actual vessel pressure at '+ri('32','28','36')+' bar -- within normal range. Transmitter fault confirmed; work order raised.'),
        energy=['pressure'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Equipment failure', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('JSA for proposed tank venting activity identified an explosion risk from flammable vapours. Mitigations: area gas test, no ignition sources within 15 m, fire watch, atmospheric monitoring. All mitigations implemented before work commenced. Completed safely.'),
        energy=['chemical','pressure'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Shift handover note flagged a critical condition on '+ri('tower T-301','reactor R-04')+'. Investigation revealed this referred to a process yield deviation, not a safety hazard. All safety systems operational. Process team addressing yield through corrective action.'),
        energy=[], barrier_phrase=None, barrier_status='n/a', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
    lambda: dict(
        text=('Security reported smoke observed at Unit-'+ri('2','4')+' perimeter. Investigated by safety officer. Confirmed to be steam venting from the '+ri('atmospheric relief vent','condensate receiver')+' -- normal operational condition in cold weather. No fire, no injury. Security team briefed.'),
        energy=['thermal'], barrier_phrase=None, barrier_status='intact', iogp=[], cause='Others', incident=ri('Unsafe Condition'), hi_po=False),
]

AMBIGUOUS = [
    lambda: dict(text='Incident near valve area. Worker says something happened during shift. Supervisor contacted. Details unclear. Under investigation.'),
    lambda: dict(text='Report from '+ri('contractor crew','field team','night shift')+' regarding something observed near '+ri('tank T-07','pump area','unit boundary')+'. No further details at this time.'),
    lambda: dict(text='Verbal report of a near miss at the '+ri('gas plant','pipeline station','well site')+'. Location and nature of incident not fully established. Awaiting written account.'),
    lambda: dict(text='Worker reported discomfort after working near '+ri('the separator','a pump skid','a pipe trench')+' in the afternoon. Medical consulted. Cause uncertain -- heat, fatigue, or exposure. Under review.'),
    lambda: dict(text='Something noticed near the '+ri('loading area','tank bund','compressor bay')+' during shift handover. Not clear if unsafe act or pre-existing condition. Safety officer to follow up.'),
    lambda: dict(text="Anonymous drop-box report: 'safety concern at unit 4 during the last week, please check.' No specific details or date given."),
    lambda: dict(text='Control room logged abnormal reading on '+ri('PI-201','TI-305','FI-117')+' at '+str(random.randint(0,23)).zfill(2)+':'+ri('10','25','40')+'. Returned to normal in 3 minutes. Cause unknown -- instrument fault or process transient.'),
    lambda: dict(text='Night shift crew reported a sound from the direction of the compressor bay. Inspection found nothing. Sound not reproduced. Cause unknown.'),
    lambda: dict(text='Contractor reported they felt unsafe during work near the wellhead but could not specify the concern. Work stopped pending investigation.'),
    lambda: dict(text='Photo on safety channel shows what appears to be a leak near a joint, but location and timestamp are unidentifiable. Field team investigating all joints in the area.'),
]

OOD = [
    lambda: dict(text='Security footage shows unidentified person accessing pipeline valve compound at '+str(random.randint(1,4)).zfill(2)+':'+ri('10','35','50')+' hrs. Individual adjusted valve position and left. Footage preserved. Police notified.', cause='Pilferage/miscreant activities'),
    lambda: dict(text='Protest gathering of approximately '+str(random.randint(30,80))+' persons blocking the main access road to the '+ri('refinery main gate','pipeline pump station')+'. Emergency vehicle access impeded. District administration liaison ongoing.', cause='Others'),
    lambda: dict(text='Suspected substance abuse: shift supervisor found one contract worker behaving incoherently. Worker tested positive for alcohol. Removed from site. Contractor management and legal provisions invoked.', cause='Others'),
    lambda: dict(text='Dead fish observed in drainage canal '+ri('500 m','1.2 km','800 m')+' downstream of the effluent treatment plant. Samples collected. Regulatory notification initiated. No direct personnel safety incident.', cause='Others'),
    lambda: dict(text='Wildfire encroaching from the '+ri('eastern','northern')+' boundary of the pipeline right-of-way. Fire originated outside company premises. External fire brigade called. No personnel in affected area.', cause='Others'),
    lambda: dict(text='Unauthorised drone observed hovering over the '+ri('refinery CDU area','LPG storage','compressor complex')+' for approximately '+str(random.randint(4,15))+' minutes. Reported to CISF and regulatory authority.', cause='Others'),
    lambda: dict(text='Theft of '+ri('copper earthing conductor','instrument air tubing','cable from cable tray')+' discovered during morning inspection. Approximately '+str(random.randint(5,20))+' metres taken. Security report filed.', cause='Pilferage/miscreant activities'),
]

OCR_BASES = [
    'Worker found working at height without harness near tank farm',
    'Gas leak detected near pump area isolation required immediately',
    'Hot work permit not obtained before grinding operations started',
    'Interlock bypassed on compressor high pressure trip system',
    'Confined space entry without gas testing H2S risk present',
    'Electrical panel live contact during maintenance LOTO absent',
    'Pressure vessel relief valve found isolated block valve closed',
    'SIMOPS assessment not done concurrent pressure test ongoing',
    'Tank truck earthing cable missing product loading commenced',
    'Scaffold inspection tag not in place workers using structure',
]

def garbled_text():
    base = random.choice(OCR_BASES)
    mode = random.randint(0,4)
    if mode == 0:
        return base[:random.randint(5,15)] + ' [OCR FAIL]'
    elif mode == 1:
        return ''.join(c if random.random() > 0.18 else random.choice('?^*~') for c in base)
    elif mode == 2:
        return base.replace('a','@').replace('e','3').replace('o','0').replace('i','1') + ' [SCAN ARTIFACT]'
    elif mode == 3:
        return base[:random.randint(8,20)] + '... [TEXT TRUNCATED - PAGE BOUNDARY]'
    else:
        mid = base[random.randint(3,10):random.randint(20,30)]
        return '### ' + mid + ' ### [GARBLED]'

def make_record(rpt_idx, difficulty, missing_meta):
    site_name, sector = random.choice(ALL_SITES)
    equip = random.choice(EQUIPMENT)
    if missing_meta:
        equip = None
        site_name = sector
    base = {
        'report_id': f'RPT-{rpt_idx:04d}',
        'site': site_name, 'date': rnd_date(),
        'shift': random.choice(SHIFTS), 'equipment_type': equip,
        'reporter_role': random.choice(REPORTER_ROLES),
    }
    if difficulty == 'garbled':
        base.update({'report_text': garbled_text(), 'incident_type': None, 'sif_precursor': None,
            'energy_types': None, 'barrier_status': None, 'barrier_phrase': None, 'iogp_rule_tags': None,
            'cause_category': None, 'severity_provenance': None, 'hi_po': None,
            'fatality_count': 0, 'injury_count': 0, 'lost_man_days': 0,
            'record_difficulty': 'garbled', 'language_note': 'English'})
        return base
    if difficulty == 'clear_positive':
        sc = random.choice(CLEAR_POS)(); sif = True
    elif difficulty == 'hard_positive':
        sc = random.choice(HARD_POS)(); sif = True
    elif difficulty == 'hard_negative':
        sc = random.choice(HARD_NEG)(); sif = False
    elif difficulty == 'ambiguous':
        sc = random.choice(AMBIGUOUS)()
        for k,v in [('energy',[]),('barrier_phrase',None),('barrier_status','n/a'),
                    ('iogp',[]),('cause','Others'),('incident','Near Miss'),('hi_po',False)]:
            sc.setdefault(k,v)
        sif = False
    elif difficulty == 'ood':
        sc = random.choice(OOD)()
        for k,v in [('energy',[]),('barrier_phrase',None),('barrier_status','n/a'),
                    ('iogp',[]),('incident','Unsafe Condition'),('hi_po',False)]:
            sc.setdefault(k,v)
        sif = False
    else:
        sc = random.choice(CLEAR_NEG)()
        for k,v in [('energy',[]),('barrier_phrase',None),('barrier_status','n/a'),
                    ('iogp',[]),('cause',ri('Non-compliance to PPE/fall and slip','Others','Inadequate supervision')),
                    ('hi_po',False)]:
            sc.setdefault(k,v)
        sif = False
    incident = sc.get('incident','Near Miss')
    hi_po    = sc.get('hi_po',False)
    lang     = sc.get('language_note','English')
    cause    = sc.get('cause',random.choice(CAUSE_CATEGORIES))
    fat,inj,lmd = 0,0,0
    if incident == 'Major Incident':
        fat = random.choice([0,0,1]); inj = random.randint(0,3); lmd = random.randint(0,90)
    elif incident == 'Minor Incident':
        inj = random.choice([0,1]); lmd = random.randint(0,15)
    if fat > 0 or incident == 'Major Incident':
        sev = 'Case Study'
    elif incident in ('Hi-Po Near Miss','Minor Incident') or sif:
        sev = ri('Safety Alert','Safety Alert','Case Study')
    else:
        sev = ri('Routine','Routine','Safety Alert')
    base.update({
        'report_text': sc['text'], 'incident_type': incident, 'sif_precursor': sif,
        'energy_types': sc.get('energy',[]), 'barrier_status': sc.get('barrier_status','n/a'),
        'barrier_phrase': sc.get('barrier_phrase'), 'iogp_rule_tags': sc.get('iogp',[]),
        'cause_category': cause, 'severity_provenance': sev, 'hi_po': hi_po,
        'fatality_count': fat, 'injury_count': inj, 'lost_man_days': lmd,
        'record_difficulty': difficulty, 'language_note': lang,
    })
    return base

TOTAL=3000; N_GARBLED=43; N_AMBIGUOUS=150; N_OOD=90; N_SIF=660
N_CLEAR_POS=396; N_HARD_POS=264
N_NEG_POOL=TOTAL-N_GARBLED-N_AMBIGUOUS-N_OOD-N_SIF
N_HARD_NEG=514; N_CLEAR_NEG=N_NEG_POOL-N_HARD_NEG

PLAN = (['clear_positive']*N_CLEAR_POS + ['hard_positive']*N_HARD_POS +
        ['clear_negative']*N_CLEAR_NEG + ['hard_negative']*N_HARD_NEG +
        ['ambiguous']*N_AMBIGUOUS + ['ood']*N_OOD + ['garbled']*N_GARBLED)
random.shuffle(PLAN)
MISSING_META_IDX = set(random.sample(range(TOTAL), int(TOTAL*0.05)))

print('Generating 3000 synthetic Oil and Gas safety reports...')
records = []
for idx, diff in enumerate(PLAN):
    missing = (idx in MISSING_META_IDX) and (diff != 'garbled')
    records.append(make_record(idx+1, diff, missing))
print(f'  {len(records)} records generated.')

OUT_DIR = Path('data/synthetic')
OUT_DIR.mkdir(parents=True, exist_ok=True)

print('\nWriting batch files...')
for b in range(6):
    batch = records[b*500:(b+1)*500]
    path  = OUT_DIR / f'batch_{b+1:02d}.jsonl'
    with open(path,'w',encoding='utf-8') as f:
        for r in batch:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'  Batch {b+1:02d} -> {path}  ({len(batch)} records)')

master = OUT_DIR / 'synthetic_oilgas_3000.jsonl'
with open(master,'w',encoding='utf-8') as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f'\n  Master -> {master}  ({len(records)} records)')

sif_n  = sum(1 for r in records if r.get('sif_precursor') is True)
non_sif= sum(1 for r in records if r.get('sif_precursor') is False)
null_n = sum(1 for r in records if r.get('sif_precursor') is None)
diff_c = {}; lang_c = {}
for r in records:
    d=r.get('record_difficulty','unknown'); diff_c[d]=diff_c.get(d,0)+1
    l=r.get('language_note','English');     lang_c[l]=lang_c.get(l,0)+1
miss_n = sum(1 for r in records if r.get('equipment_type') is None)

print('\n'+'='*55)
print('  DATASET STATISTICS')
print('='*55)
print(f'  Total records    : {TOTAL}')
print(f'  SIF positive     : {sif_n}  ({sif_n/TOTAL*100:.1f}%)')
print(f'  SIF negative     : {non_sif}  ({non_sif/TOTAL*100:.1f}%)')
print(f'  Null / garbled   : {null_n}  ({null_n/TOTAL*100:.1f}%)')
print(f'  Missing metadata : {miss_n}  ({miss_n/TOTAL*100:.1f}%)')
print()
for d,c in sorted(diff_c.items()):
    print(f'  {d:22s}: {c:5d}  ({c/TOTAL*100:.1f}%)')
print('='*55)
print('\nDone.')
