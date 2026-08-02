# Perkeo

See [README.md](README.md) for info about Wednesware Lithium.

## Overview

Perkeo is a function-oriented programming language designed around a simple principle:

> All language operations are represented as function calls.

Syntax exists primarily for readability. Most language features are implemented as normal functions receiving values, named arguments, and optional child blocks.

---

## Execution Model

### Functions

Functions are the primary unit of execution.

A function may receive:

- Positional arguments
- Named arguments
- An optional child block

Example:

```perkeo
print "hello, world!"
````

Functions decide how their arguments and child blocks are interpreted.

---

## Positional Arguments

The first positional argument is called `value`.

Example:

```perkeo
print "hello"
```

is equivalent to:

```perkeo
print value::"hello"
```

Multiple positional arguments are collected into a list.

Example:

```perkeo
string 4 5
```

is equivalent to:

```perkeo
string [4, 5]
```

For a function whose only parameter is `value`, an unparenthesized operator
expression is evaluated as that value:

```perkeo
print 3 + 2
```

To pass separate values, use commas. Commas also separate array entries:

```perkeo
print 3, +, 2
print [3, +, 2]
```

Calls that accept keyword parameters preserve an unparenthesized operator
sequence as positional values. For example, `fn_with_kw 3 + 2 myarg::4` receives
`value::[3 + 2]` and `myarg::4`; parenthesize the expression to pass its result.

---

### Named Arguments

Named arguments use the syntax:

```perkeo
name::value
```

Example:

```perkeo
print "hello" color::red
```

Repeated named arguments are collected into a list.

Example:

```perkeo
example value::1 value::2
```

is equivalent to:

```perkeo
example value::[1, 2]
```

---

### Child Blocks

Functions may optionally receive a child block.

Syntax:

```perkeo
function arguments -> (
    code
)
```

Example:

```perkeo
if condition -> (
    print "true"
)
```

Functions determine how child blocks are executed.

---

## Objects

### Maps

Objects are maps.

Maps contain key-value pairs and are the foundation of:

* Objects
* Classes
* Namespaces
* Argument maps

---

### Types

Types are runtime objects.

Examples:

```
integer
float
string
boolean
map
function
library
```

User-created classes create new runtime types.

---

### Functions

Functions are inspectable objects.

Functions contain metadata such as:

* Arguments
* Return information
* Child block behavior
* Source information

---

## Calling Functions

### Normal Invocation

Standard function call:

```perkeo
print "hello"
```

---

### Mapped Invocation

The `*` suffix enables mapped invocation.

Example:

```perkeo
print* {
    "hello"
}
```

This passes one or more maps as argument templates.

The `*` suffix does not specifically mean "call"; it means that arguments are provided through maps.

Example:

```perkeo
hello*
```

is an argument-less mapped invocation.

---

### Explicit Invocation

The `call` function explicitly invokes a function.

Examples:

```perkeo
call hello
```

```perkeo
call hello "world"
```

This is useful when a function object needs to be called without ambiguity.

---

## Variables

### Assignment

Variables are created and modified using `set`.

Example:

```perkeo
set number to::30
```

If the variable does not exist, it is created.

If it exists, its value is replaced.

---

### Constants

Constants are immutable variables.

Example:

```perkeo
const pi to::3.14159
```

Constants cannot be reassigned.

---

## Classes

Classes are maps with special metadata.

A class contains:

* Constructor functions
* Method functions
* Instance behavior

Creating a class creates a new runtime type.

Example:

```perkeo
class Person -> (
    constructor name::string -> (
        public name
    )
)
```

Objects created from classes are still maps internally.

### Constructors

Declare a class-local `constructor` function to initialize each instance. `new`
passes its keyword arguments to that function, and `me` refers to the new
instance.

```perkeo
class Person -> (
    fn constructor name::string -> (
        me.name::name
    )
)

person::(new Person name::"Ada")
```

### Custom Units

`pko.std` exports the `unit` base class. A unit class uses `scale` in the form
`[numerator:denominator referenceUnit]`: one new unit equals that fraction of
the reference unit.

```perkeo
class ft inherits::unit -> (
    scale::[1:1 m]
)

class inch inherits::unit -> (
    scale::[1:12 ft]
)

print (12inch to ft)
```

### Unit Libraries

Unit families are imported explicitly and can be combined in one program:

```perkeo
import pko.metric.ALL
import pko.imperial.ALL
import pko.ui.ALL
import pko.computer.ALL
```

`pko.metric` includes SI prefixes plus area and volume units such as `m2`,
`cm2`, `m3`, `L`, and `mL`. `pko.imperial` includes `inch`, `ft`, `yd`, `mi`,
`mile`, `acre`, `gal`, `lb`, and related customary units. `pko.ui` supplies
display units including `px`, `dp`, `sp`, `em`, `rem`, `csspt`, `ppi`, `dpi`,
and `mp`. `pko.computer` supplies decimal and binary information units from
`bit` and `byte` through `TB` and `TiB`.

```perkeo
print (10000cm2 to m2)
print (12inch to ft)
print (2rem to px)
print (1MiB to bytes)
```

### Custom Operators

`pko.std` also exports the `operator` base class. Define a symbolic `symbol`
and an `apply` function with two parameters. User-defined symbols use the same
precedence as `+` and `-`.

```perkeo
class Sum inherits::operator -> (
    symbol::"%%"

    fn apply left::integer right::integer -> (
        left + right
    )
)

print (2 %% 3)
```

---

## Argument Constraints

Argument declarations may define expected input types.

### Runtime Types

Runtime types describe values received by functions.

Examples:

```perkeo
type::string
type::integer
type::map
type::function
```

---

### Context Types

Context types describe source-level values provided by the compiler.

Examples:

```perkeo
type::ctx.identifier
type::ctx.block
```

These are not runtime types and do not appear in `ctx.types`.

---

### Identifier Arguments

`type::ctx.identifier` accepts an identifier from source code and passes its name as a string.

Example:

```perkeo
fn hello name::type::ctx.identifier -> (
    print name
)
```

Usage:

```perkeo
hello World
```

The function receives:

```text
"World"
```

---

## Context

`ctx` is the single environment object provided by Perkeo.

It contains backend and execution information.

Examples:

```perkeo
ctx.types (list of all registered types)
ctx.import (default import method)
ctx.cwd (current working directory)
ctx.file (full current file path)
ctx.ver (perkeo interpreter/runtime version)
ctx.pf (current os)
ctx.op (list of operator functions like addition, subtraction, etc.)
ctx.err (list of all registered errors)
```

---

## Returns

Functions may return any object.

Example:

```perkeo
return value
```

Returning exits the current block.

The number of exited blocks may be specified:

```perkeo
return value layers::2
```

---

## Syntax Sugar

Syntax sugar is converted into normal function calls internally.

---

### Strings

```perkeo
"hello"
```

is equivalent to a string constructor call.

---

### Lists

```perkeo
[1, 2, 3]
```

is equivalent to a list constructor call.

---

### Operators

Operators are function calls with shorter syntax.

Example:

```perkeo
a + b
```

is equivalent to:

```perkeo
ctx.op.add a b
```

Operators do not require special runtime behavior.

---

## Imports

Libraries are imported through functions.

Identifier imports:

```perkeo
import math
```

String-based imports:

```perkeo
stringimport "math"
```

Import methods may be customized through ctx.

---

## Reflection

Perkeo objects expose metadata.

Examples:

```perkeo
function.arguments
function.return_type
class.methods
ctx.types
```

Reflection is a core feature of the language.

---

## Design Principles

1. Everything that performs an action is a function.
2. Syntax should lower into normal operations where possible.
3. Objects are maps.
4. Functions are objects.
5. Blocks are values passed to functions.
6. Runtime values and source-level syntax are separate concepts.
7. The language should prefer consistency over special cases.