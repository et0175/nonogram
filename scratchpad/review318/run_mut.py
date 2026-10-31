import sys; sys.path.insert(0,"/Users/omelnikova/PycharmProjects/PythonProject4-card-318/scratchpad/review318")
from mutate import mutant
RAND="tests/test_solver_strategies.py::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::test_a_random_batch_stores_a_real_list_for_every_row"
IMG ="tests/test_solver_strategies.py::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::test_an_image_batch_stores_a_real_list_for_every_row"
# R1: reproduce M6 — empty list at the random call site
mutant("R1 M6-repro random -> []","src/nonogram/admin/batch_generator.py",
       "strategies_used=list(puzzle.strategies),","strategies_used=[],",[RAND])
# R2: reproduce M9 — empty list at the image call site
mutant("R2 M9-repro image  -> []","src/nonogram/admin/app.py",
       "strategies_used=list(puzzle.strategies),","strategies_used=[],",[IMG])
# R3: THE SHARP ONE — a plausible, in-vocabulary but WRONG constant list (random)
mutant("R3 random -> hardcoded ['simple_overlap']","src/nonogram/admin/batch_generator.py",
       "strategies_used=list(puzzle.strategies),","strategies_used=['simple_overlap'],",[RAND])
# R4: same, image path
mutant("R4 image  -> hardcoded ['simple_overlap']","src/nonogram/admin/app.py",
       "strategies_used=list(puzzle.strategies),","strategies_used=['simple_overlap'],",[IMG])
