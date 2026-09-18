# Marks this directory as a package so that pytest imports the test modules
# under it by their full dotted path (qatrack.<app>.tests.test_x) rather than
# by bare module name. Without it, two test files that share a basename -
# test_views.py and test_models.py both exist in several apps - collide in
# sys.modules and collection fails with an "import file mismatch" error.
