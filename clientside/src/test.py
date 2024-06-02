# main.py
from .ot_tracer import trace_function

@trace_function
def example_function(a, b):
    return a + b

@trace_function
def another_example_function(x):
    return x * x

if __name__ == "__main__":
    result = example_function(1, 2)
    print(f"Result of example_function: {result}")
    
    result = another_example_function(3)
    print(f"Result of another_example_function: {result}")
