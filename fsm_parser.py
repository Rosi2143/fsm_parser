#! /usr/bin/python3
# MIT License
# 
# Copyright (c) 2020 Michael Rossner
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

import re, subprocess, os, json, argparse, copy, shutil , inspect, sys
from typing_extensions import TypedDict
from datetime import datetime
from typing import *

scriptVersion : str = "2.3"

fsmName : str = "none"
context : str = "none"
initial : str = "none"
version : str = "none"

TransitionType = TypedDict('TransitionType', {'event'			: str,
                                              'nextState'		: Optional[str],
                                              'guardList'		: List[str],
                                              'eventsSendList'	: List[str],
                                              'actionList'		: List[str]
                                              }
                           )
newTransition : TransitionType = {
		  'event'             : "",
		  'nextState'         : "",
		  'guardList'         : [],
		  'eventsSendList'    : [],
		  'actionList'        : []
		}

StateType = TypedDict('StateType', {'parentState'		: str,
                                    'stateName'			: str,
                                    'entryFunctionList'	: List[str],
                                    'exitFunctionList'	: List[str],
                                    'defaultTransition'	: Optional[TransitionType],
                                    'transitionList'	: List[TransitionType],
                                    'childStateList'	: List[Any]
                                    }
                      )
newState : StateType = {
		 'parentState'        : "",
		 'stateName'          : "",
		 'entryFunctionList'  : [],
		 'exitFunctionList'   : [],
		 'defaultTransition'  : None,
		 'transitionList'     : [],
		 'childStateList'     : []
		}

insideActionBlock : bool = False
insideEventBlock  : bool = False

state_list : List[StateType] = []
currentState : StateType = newState

inputFile  : str = ""
outputFile : str = ""

parser = argparse.ArgumentParser(prog='fsm_parser', description="parses SMC description files and generates PlantUML files.", epilog="Requirements: * plantuml via 'sudo apt-get install plantuml'")
parser.add_argument("--version", action='version', version='%(prog)s ' + scriptVersion)
parser.add_argument("-v", "--verbose", help="activates debug output", action="store_true")
parser.add_argument("-f", "--fsmFile", nargs=1, action='store', type=str, help="path to fsm-file")
parser.add_argument("-a", "--showAll", help="show all element in PlantUML == -e -g -t", action="store_true")
parser.add_argument("-e", "--showEntryExitActions", help="show entry and exit actions in PlantUML", action="store_true")
parser.add_argument("-g", "--showGuards", help="show guard conditions in PlantUML", action="store_true")
parser.add_argument("-t", "--showTransitionActions", help="show transition actions in PlantUML", action="store_true")
parser.add_argument("-p", "--generatePicture", help="run plantUML to generate a picture graph", action="store_true")
parser.add_argument("-x", "--extraParameter", nargs=1, action='store', type=str, help="pass extra parameter to plantuml. e.g. \"tsvg teps\"")
args = parser.parse_args()

if not args.fsmFile: 
    parser.print_help()
    quit(1)

if args.verbose: print("*.fsm-File = ", args.fsmFile[0])
if (args.verbose and args.extraParameter): print("umlplant Parameter = ", args.extraParameter[0])


def addState(node : List[StateType], line : str) -> Optional[StateType]:
	ret_state : Optional[StateType] = None
	for state in node:
		if state['childStateList']:
			ret_state = addState(state['childStateList'], line)
		if args.verbose: print("checking state = ",{state['stateName']})
		reg = re.search("^\s*(\w*)\s*:\s*"+state['stateName'], line)
		if reg:
			if args.verbose: print("State ", reg.group(1), " found")
			myState = copy.deepcopy(newState)
			myState['parentState'] = state['stateName']
			myState['stateName']   = reg.group(1)
			state['childStateList'].append(myState)
			ret_state = myState
			break
	return ret_state

def exportStates(node : List[StateType], indent_depth : int = 0) -> str :
	ret_state 		: str = ""
	indent_string 	: str = "   "
	for state in node:
		if args.verbose: print("exporting state = ", state['stateName'])
		ret_state += indent_string * indent_depth + "state " + state['stateName'] + " {\n"

		if state['childStateList']:
			ret_state += exportStates(state['childStateList'], indent_depth + 1)

		if state['defaultTransition'] is not None:
			if args.verbose: print("\tDefaultTransition = ", state['defaultTransition']['nextState'])
			if state['defaultTransition']['nextState'] is not None:
				ret_state += indent_string * (indent_depth + 1) + "[*] --> " + state['defaultTransition']['nextState'] + "\n"

		if (args.showEntryExitActions or args.showAll):  
			if state['entryFunctionList']:
				for entryFunction in state['entryFunctionList']:
					if args.verbose: print("\tentry Function = ", entryFunction)
					ret_state += indent_string * (indent_depth + 1) + state['stateName'] + " : entry / " + entryFunction + "()\n"

			if state['exitFunctionList']:
				for exitFunction in state['exitFunctionList']:
					if args.verbose: print("\texit Function = ", exitFunction)
					ret_state += indent_string * (indent_depth + 1) + state['stateName'] + " : exit / " + exitFunction + "()\n"

		if state['transitionList']:
			for transition in state['transitionList']:
				if transition['nextState']:
					if args.verbose: print("\texporting transition = ", transition['event'], " --> ", transition['nextState'])
					if transition['nextState'] is not None:
						ret_state += indent_string * (indent_depth + 1) + state['stateName'] + " --> " + transition['nextState'] + " : " + transition['event']
				else:
					if args.verbose: print("\texporting internal transition = ", transition['event'])
					ret_state += indent_string * (indent_depth + 1) + state['stateName'] + " : " + transition['event']
				if transition['guardList'] and (args.showGuards or args.showAll):
					ret_state += "[" + ' '.join(transition['guardList']) + "]"

				if transition['actionList'] and (args.showTransitionActions or args.showAll):
					ret_state += " / " + ' '.join(transition['actionList'])

				ret_state += "\n"

		ret_state += indent_string * indent_depth + "}\n\n"
	return ret_state

if not shutil.which("plantuml"):
    print("Program plantuml does not exist. Please install it.\nSee https://plantuml.com/download")
    quit(1)

if not subprocess.check_output("plantuml -testdot", stderr=subprocess.STDOUT, shell=True):
    print("Program plantuml cannot find 'dot'. Please install it.")
    quit(2)


inputFile = args.fsmFile[0]
with open(inputFile, "r") as fsmFile:
	line : str = " "
	lineCount : int = 1
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
			print("FSMName=", fsmName)

		reg = re.search("^\s*Context\s+(\w+)", line, re.IGNORECASE)
		if reg:
			context = reg.group(1)
			print("Context=", context)

		reg = re.search("^\s*Initial\s+(\w+)", line, re.IGNORECASE)
		if reg:
			initial = reg.group(1)
			print("Initial=", initial)

		reg = re.search("^\s*Version\s+(.*)", line, re.IGNORECASE)
		if reg:
			version = reg.group(1)
			print("version=", version)

		###################################
		# find root state
		###################################
		reg = re.search("^\s*\(\s*"+initial+"\s*\)", line)
		if reg:
			if args.verbose: print("Toplevel found")
			myState : StateType = copy.deepcopy(newState)
			myState['parentState'] = "Root"
			myState['stateName']   = initial
			state_list.append(myState)
			currentState = myState

		###################################
		# find any state - with parent state
		###################################
		tempState : Optional[StateType] = addState(state_list, line)
		if tempState:
			currentState = tempState
		
		if args.verbose: print("currentState = ", json.dumps(currentState, indent=2))

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
				entryFunction : str = reg.group(1)
				if args.verbose: print("entryFunction = ", entryFunction)
				currentState['entryFunctionList'].append(entryFunction)
			reg = re.search("^\s*exit\s+(\w+)", line)
			if reg:
				exitFunction : str = reg.group(1)
				if args.verbose: print("exitFunction = ", exitFunction)
				currentState['exitFunctionList'].append(exitFunction)
			reg = re.search("^\s*Default\s+(\w+)\s+\{([\w\s]*)\}", line, re.IGNORECASE)
			if reg:
				defaultTransition : TransitionType = copy.deepcopy(newTransition)
				defaultTransition['nextState'] = reg.group(1)
				defaultTransition['actionList'] = reg.group(2).split()
				defaultTransition['actionList'] = ["{}()".format(element) for element in defaultTransition['actionList'] ]
				if args.verbose: print("defaultTransition = ", defaultTransition)
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
				selfTransition : TransitionType = copy.deepcopy(newTransition)
				selfTransition['event']     	 = reg.group(1)
				selfTransition['nextState'] 	 = None
				selfTransition['guardList']      = reg.group(2).split()
				selfTransition['eventsSendList'] = reg.group(3).split()
				selfTransition['actionList']	 = ["{}()".format(element) for element in reg.group(4).split() ]
				if args.verbose: print("selfTransition = ", selfTransition)
				currentState['transitionList'].append(selfTransition)
			reg = re.search("^\s*(\w*)\s+(\w+)\s+\{([\w\s]*)\}\s+\{([\w\s]*)\}\s+\{([\w\s]*)\}", line)

			if reg:
				Transition : TransitionType = copy.deepcopy(newTransition)
				Transition['event']          = reg.group(1)
				Transition['nextState']  	 = reg.group(2)
				Transition['guardList']      = reg.group(3).split()
				Transition['eventsSendList'] = reg.group(4).split()
				Transition['actionList']     = reg.group(5).split()
				if args.verbose: print("Transition = ", Transition)
				currentState['transitionList'].append(Transition)
	fsmFile.close()

if args.verbose: print("json = ", json.dumps(state_list, indent=2))

###################################
# create PlantUML file
###################################
outputFile = inputFile.replace(".fsm", ".plantuml")
if args.verbose: print("Writing to file ", outputFile)

with open(outputFile, "w") as plantUmlFile:
	plantUmlFile.write("@startuml\n")
	plantUmlFile.write("' generated file\n")
	plantUmlFile.write("' command:\n")
	plantUmlFile.write("'     " + " ".join(sys.argv[0:]) + "\n")
	plantUmlFile.write("' version:\n")
	plantUmlFile.write("'     " + scriptVersion + "\n")
	plantUmlFile.write("' datetime:\n")
	plantUmlFile.write("'     " + str(datetime.now()) + "\n")
	plantUmlFile.write(exportStates(state_list))
	plantUmlFile.write("@enduml")
	plantUmlFile.close()
 
print("#########################################################\nOutput file generated at ", outputFile)

if (args.generatePicture or args.showAll):
	additionalArgs : str = ""
	if args.extraParameter:
		additionalArgs = "-" + " -".join(args.extraParameter[0].split())
		if args.verbose: print("additionalArgs = ", additionalArgs)
	subprocess.run(["plantuml", outputFile, additionalArgs])
