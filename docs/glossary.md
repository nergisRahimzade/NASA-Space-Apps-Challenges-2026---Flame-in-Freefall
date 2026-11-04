## 1- MUST KNOW

- Microgravity: 
  - Plain: The near-weightless state in space where everything floats because it is constantly falling. In microgravity, fire burns as a small, round blue ball because without gravity to pull hot air upward, oxygen feeds the flame evenly from all directions.
  - Technical: Near-weightless conditions (about one-millionth of Earth's gravity) on the ISS (International Space Station). There is no buoyancy, so flames get oxygen only by slow mixing (diffusion). That's why a candle flame turns into a dim blue ball.
- Flame spread: 
  - Plain: How fst fire moves across a material.
  - Technical: Flame spread rate, usually im mm/s or cm/s. This is likely our main number in master.csv.
- LOI (Limiting Oxygen Index):
  - Plain: The lowest oxygen level at which somethign keeps burning.
  - Technical: The minimum O2% neede to sustain burning, form a standard Earth test. Lower LIO means more dangerous. NASA's realted term is MOC (Maximum Oxygen Concentration), the highest O2% at which a material is still considered safe.
- BASS / BASS-II (Burning and Suppression of Solids): 
  - Plain: Small ISS tests that burned fabrics and plastics in moving air.
  - Technical: Run in the Microgravity Science  Glovebox using a small fan-driven flow duct. Variables were material, oxygen % and airflow speed.
- FLEX / FLEX-2 (Flame Extinguishment Experiment):
  - Plain: Burning tiny fuel drops an testing how to put them ou.
  - Technical: Droplet combustion in the MDCA. Suppression came from diluting the air with CO2 or helium. FLEX also discovered cool flames, which are invisible, low-temperature burning that continues after the visible flame goes out.
- Saffire-I, -II, -III (Spacecraft Fire Safety Demonstration):
  - Plain: Big, real-size fires lit on purpose inside a cargo ship after it left the ISS. 
  - Technical: Large-scale material flmmability tests on uncrewed Cygnus vehicles. This is the closest data to a real spacecraft fire.

## 2 - Good to Know: Fire-Safety Words

- Prevention / Detection / Suppression: Stop fire from starting, notice it early, put it out. This is NASA’s three-part framework.
- Flammability Limit: The condition (oxygen %, pressure, airflow) where fire can or can’t survive. 
- Ignition: What starts the fire.
- Extinction: When the flame dies.
- Opposed vs. Concurrent Flow: Air blowing against the direction the flame moves vs. with it. Concurrent flow spreads faster.
- Oxygen Concentration and Pressure (psi): Earth is about 21% O₂ at 14.7 psi. A Moon base would be about 30% O₂ at 10.2 psi or less. More oxygen makes materials more flammable.
- Soot / Smoke Point: Soot is the black particles in smoke. Smoke point is how tall a flame gets before it starts releasing soot.
- Partial Gravity: Moon or Mars gravity. There's no data for it in PSI (Physical Sciences Informatics) yet.


## 3 - Names we'll see while browsing PSI on Day 3

- PSI: NASA’s Physical Science Informatics database, where the data lives.
- ISS: International Space Station.
- CIR: Combustion Integrated Rack.
- MDCA: The droplet burner inside the CIR.
- MSG: Microgravity Science Glovebox.
- ACME: A set of 6 gas-flame experiments, including BRE, CFI-G, and E-FIELD.
- SAME / SAME-R: Smoke detection experiments.
- SPICE / SLICE: Gas-flame experiments in the same flow duct as BASS.

## 4 - Data Words: What our columns will hold

- Plain: What was burned, under what conditions, and what happened.
- 
- Technical: 
  - Sample: Material, shape, size, thickness.
  - Test conditions: O₂ %, pressure, flow speed. 
  - Measurements: spread rate, flame length, extinction yes/no, and which sensors took them (camera, thermocouple).
