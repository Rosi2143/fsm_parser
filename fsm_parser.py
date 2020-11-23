#! /usr/bin/python3
# MIT License
# 
# Copyright (c) 2020 Michael Roßner
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# parse fsm-files of SMC generator to create diagrams
# check these pages for useof  state machine UML
#    * https://en.wikipedia.org/wiki/UML_state_machine#Guard_conditions
#    * https://sparxsystems.com/resources/tutorials/uml2/state-diagram.html
#
# run on all *.fsm files
# find . -type f -name "*.fsm" -exec python3 fsm_parser.py --fsmFile {} -a \;

import re, subprocess, os, json, argparse, copy

fsmName = "none"
context = "none"
initial = "none"
version = "none"
newState={
		 'parentState'        : "",
		 'stateName'          : "",
		 'entryFunction'      : [],
		 'exitFunction'       : [],
		 'defaultTransition'  : {},
		 'transitionList'     : [],
		 'childStateList'     : []
	   }
newTransition={
		  'event'             : "",
		  'nextState'         : "",
		  'guards'            : [],
		  'eventsSend'        : [],
		  'actions'           : []
	   }

insideActionBlock = False
insideEventBlock = False

state_list = []
currentState = None

inputFile  = ""
outputFile = ""

parser = argparse.ArgumentParser(prog='fsm_parser', description="parses SMC description files and generates PlantUML files.", epilog="Requirements: * plantuml via 'sudo apt-get install plantuml'")
parser.add_argument("--version", action='version', version='%(prog)s 2.0')
parser.add_argument("-v", "--verbose", help="activates debug output", action="store_true")
parser.add_argument("-f", "--fsmFile", nargs=1, action='store', type=str, help="path to fsm-file")
parser.add_argument("-a", "--showAll", help="show all element in PlantUML == -e -g -t", action="store_true")
parser.add_argument("-e", "--showEntryExitActions", help="show entry and exit actions in PlantUML", action="store_true")
parser.add_argument("-g", "--showGuards", help="show guard conditions in PlantUML", action="store_true")
parser.add_argument("-t", "--showTransitionActions", help="show transition actions in PlantUML", action="store_true")
parser.add_argument("-p", "--generatePicture", help="run plantUML to generate a picture graph", action="store_true")
parser.add_argument("-x", "--extraParameter", nargs=1, action='store', type=str, help="pass extra parameter to plantuml. e.g. \"tsvg teps\"")
args = parser.parse_args()

if args.verbose: print(f"File = {args.fsmFile[0]}")
if (args.verbose and args.extraParameter): print(f"umlplant Parameter = {args.extraParameter[0]}")

if not args.fsmFile: parser.print_help()

def addState(node, line):
	ret_state = None
	for state in node:
		if state['childStateList']:
			ret_state = addState(state['childStateList'], line)
		if args.verbose: print(f"checking state = {state['stateName']}")
		reg = re.search("^\s*(\w*)\s*:\s*"+state['stateName'], line)
		if reg:
			if args.verbose: print(f"State {reg.group(1)} found")
			myState = copy.deepcopy(newState)
			myState['parentState'] = state['stateName']
			myState['stateName']   = reg.group(1)
			state['childStateList'].append(myState)
			ret_state = myState
			break
	return ret_state

def exportStates(node, indent_depth = 0):
	ret_state = ""
	indent_string = "   "
	for state in node:
		if args.verbose: print(f"exporting state = {state['stateName']}")
		ret_state += indent_string * indent_depth + "state " + state['stateName'] + " {\n"

		if state['childStateList']:
			ret_state += exportStates(state['childStateList'], indent_depth + 1)

		if state['defaultTransition']:
			if args.verbose: print(f"\tDefaultTransition = {state['defaultTransition']['nextState']}")
			ret_state += indent_string * (indent_depth + 1) + "[*] --> " + state['defaultTransition']['nextState'] + "\n"

		if (args.showEntryExitActions or args.showAll):  
			if state['entryFunction']:
				for entryFunction in state['entryFunction']:
					if args.verbose: print(f"\tentry Function = {entryFunction}")
					ret_state += indent_string * (indent_depth + 1) + state['stateName'] + " : entry / " + entryFunction + "()\n"

			if state['exitFunction']:
				for exitFunction in state['exitFunction']:
					if args.verbose: print(f"\texit Function = {exitFunction}")
					ret_state += indent_string * (indent_depth + 1) + state['stateName'] + " : exit / " + exitFunction + "()\n"

		if state['transitionList']:
			for transition in state['transitionList']:
				if transition['nextState']:
					if args.verbose: print(f"\texporting transition = {transition['event']} --> {transition['nextState']}")
					ret_state += indent_string * (indent_depth + 1) + state['stateName'] + " --> " + transition['nextState'] + " : " + transition['event']
				else:
					if args.verbose: print(f"\texporting internal transition = {transition['event']}")
					ret_state += indent_string * (indent_depth + 1) + state['stateName'] + " : " + transition['event']
				if transition['guards'] and (args.showGuards or args.showAll):
					ret_state += "[" + ' '.join(transition['guards']) + "]"

				if transition['actions'] and (args.showTransitionActions or args.showAll):
					ret_state += " / " + ' '.join(transition['actions'])

				ret_state += "\n"

		ret_state += indent_string * indent_depth + "}\n\n"
	return ret_state

# thanks to https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

if not which("plantuml"):
    print("Program plantuml does not exist. Please install it.\nSee https://plantuml.com/download")
    quit(1)

if not subprocess.check_output("plantuml -testdot", stderr=subprocess.STDOUT, shell=True):
    print("Program plantuml cannot find 'dot'. Please install it.")
    quit(1)


inputFile = args.fsmFile[0]
with open(inputFile, "r") as fsmFile:
	line = fsmFile.readline()
	lineCount = 1
	while line:
		line = fsmFile.readline()
		if args.verbose: print("\n\n##########################################\nLine {}: {}".format(lineCount, line.strip()))
		lineCount = lineCount + 1

		###################################
		# ignore comments
		###################################
		if re.search("^\s*//", line):
			if args.verbose: print("skip comment") 
			continue

		###################################
		# find header
		###################################
		reg = re.search("^\s*FSMName\s+(\w+)", line, re.IGNORECASE)
		if reg:
			fsmName = reg.group(1)
			print(f"FSMName={fsmName}")

		reg = re.search("^\s*Context\s+(\w+)", line, re.IGNORECASE)
		if reg:
			context = reg.group(1)
			print(f"Context={context}")

		reg = re.search("^\s*Initial\s+(\w+)", line, re.IGNORECASE)
		if reg:
			initial = reg.group(1)
			print(f"Initial={initial}")#

		reg = re.search("^\s*Version\s+(.*)", line, re.IGNORECASE)
		if reg:
			version = reg.group(1)
			print(f"version={version}")

		###################################
		# find root state
		###################################
		reg = re.search("^\s*\(\s*"+initial+"\s*\)", line)
		if reg:
			if args.verbose: print(f"Toplevel found")
			myState = copy.deepcopy(newState)
			myState['parentState'] = "Root"
			myState['stateName']   = initial
			state_list.append(myState)
			currentState = myState

		###################################
		# find any state - with parent state
		###################################
		tempState = addState(state_list, line)
		if tempState:
			currentState = tempState
		
		if args.verbose: print(f"currentState = {json.dumps(currentState, indent=2)}")

		###################################
		# find entry/exit actions and default states
		###################################
		if not insideActionBlock:
			reg = re.search("^\s*\[\s*", line)
			if reg:
				insideActionBlock = True
				if args.verbose: print("inside Action Block")
		
		if insideActionBlock:
			reg = re.search("^\s*entry\s+(\w+)", line)
			if reg:
				entryFunction = reg.group(1)
				if args.verbose: print (f"entryFunction = {entryFunction}")
				currentState['entryFunction'].append(entryFunction)
			reg = re.search("^\s*exit\s+(\w+)", line)
			if reg:
				exitFunction = reg.group(1)
				if args.verbose: print (f"exitFunction = {exitFunction}")
				currentState['exitFunction'].append(exitFunction)
			reg = re.search("^\s*Default\s+(\w+)\s+\{([\w\s]*)\}", line, re.IGNORECASE)
			if reg:
				defaultTransition = copy.deepcopy(newTransition)
				defaultTransition['nextState'] = reg.group(1)
				defaultTransition['actions'] = reg.group(2).split()
				defaultTransition['actions'] = ["{}()".format(element) for element in defaultTransition['actions'] ]
				if args.verbose: print (f"defaultTransition = {defaultTransition}")
				currentState['defaultTransition'] = defaultTransition

			reg = re.search("^\s*\]\s*", line)
			if reg:
				insideActionBlock = False
				if args.verbose: print ("outside Action Block")

		###################################
		# find events
		###################################
		if not insideEventBlock:
			reg = re.search("^\s*\{\s*", line)
			if reg:
				insideEventBlock = True
				if args.verbose: print ("inside Event Block")
		
		if insideEventBlock:
			reg = re.search("^\s*\}\s*", line)
			if reg:
				insideEventBlock = False
				if args.verbose: print ("outside Event Block")

			reg = re.search("^\s*(\w*)\s+\*\s+\{([\w\s]*)\}\s+\{([\w\s]*)\}\s+\{([\w\s]*)\}", line)
			if reg:
				selfTransition = copy.deepcopy(newTransition)
				selfTransition['event']      = reg.group(1)
				selfTransition['nextState']  = None
				selfTransition['guards']     = reg.group(2).split()
				selfTransition['eventsSend'] = reg.group(3).split()
				selfTransition['actions']    = reg.group(4).split()
				selfTransition['actions'] = ["{}()".format(element) for element in selfTransition['actions'] ]
				if args.verbose: print (f"selfTransition = {selfTransition}")
				currentState['transitionList'].append(selfTransition)
			reg = re.search("^\s*(\w*)\s+(\w+)\s+\{([\w\s]*)\}\s+\{([\w\s]*)\}\s+\{([\w\s]*)\}", line)

			if reg:
				Transition = copy.deepcopy(newTransition)
				Transition['event']      = reg.group(1)
				Transition['nextState']  = reg.group(2)
				Transition['guards']     = reg.group(3).split()
				Transition['eventsSend'] = reg.group(4).split()
				Transition['actions']    = reg.group(5).split()
				if args.verbose: print (f"Transition = {Transition}")
				currentState['transitionList'].append(Transition)
	fsmFile.close()

if args.verbose: print(f"json = {json.dumps(state_list, indent=2)}")

###################################
# create PlantUML file
###################################
outputFile = inputFile.replace(".fsm", ".plantuml")
if args.verbose: print(f"Writing to file {outputFile}")
with open(outputFile, "w") as plantUmlFile:
	plantUmlFile.write("@startuml\n")
	plantUmlFile.write(exportStates(state_list))
	plantUmlFile.write("@enduml")
	plantUmlFile.close()
 
print(f"#########################################################\nOutput file generated at {outputFile}")

if (args.generatePicture or args.showAll):
	additionalArgs = ""
	if args.extraParameter:
		additionalArgs = "-" + " -".join(args.extraParameter[0].split())
		if args.verbose: print(f"additionalArgs = {additionalArgs}")
	subprocess.run(["plantuml", outputFile, additionalArgs])