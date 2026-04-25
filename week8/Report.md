# A2A Travel Collaboration POC Report

This system is an A2A collaboration POC for travel booking scenarios. The system is built around combined flight and hotel search, with the data source using local mock data and not relying on external airline or hotel APIs.


The system consists of five layers:
- Interaction layer: frontend page or CLI
- API layer: unified FastAPI entry
- Orchestration layer: LangGraph Orchestrator
- Execution layer: Flight Agent and Hotel Agent
- Data layer: Mock JSON data source

Our workflow is "user input -> orchestration parsing -> conditional routing -> sub-agent execution -> result aggregation -> natural language summary -> return to frontend".

## Step 1: the user request enters the system.
The user can input natural language from the frontend page or CLI, for example, "Help me book a trip from Bangkok to Beijing on June 10, return on the 14th, and book a hotel as well."
After the request enters the unified API entry, the system first builds a standard state object as the context container for this workflow.

## Step 2: the orchestrator performs intent parsing.
The first node of the orchestrator is the intent parsing node. It combines the current input and conversation history to extract structured parameters, such as:

Intent type: flight-only search, combined flight-and-hotel search, or hotel-only search
Origin and destination candidates
Departure and return dates
Hotel city
The value of this layer is converting "natural language" into "executable parameters," so that each subsequent node can process stably.

## Step 3: conditional routing.
After obtaining the intent, the orchestrator does not follow a fixed path, but routes according to the intent:

If it is flight_only, it goes to the flight agent first
If it is flight_and_hotel, it also goes to flights first, then hotels
If it is hotel_only, it goes directly to the hotel branch
If it is other, it skips querying and directly enters the summary node
So the core is not "one large model handles everything," but "the orchestrator chooses the correct execution chain based on intent."

## Step 4: flight agent execution.
When the flow enters the flight branch, the orchestrator assembles a task object and specifies the receiver as the flight agent.
This task is sent through an A2A-style router.
After receiving it, the flight agent does only one thing: call the flight search tool.
The tool filters flight data by origin, destination, and date, and returns candidate outbound and return results.
After this step ends, the result is written back to the workflow state for use in the next step.

## Step 5: hotel agent execution.
There are two cases in the hotel branch:

hotel_only scenario:
The orchestrator first converts date and city into hotel query parameters, such as check-in window and check-out buffer time, and then sends them to the hotel agent.

Combined flight-and-hotel scenario:
The orchestrator uses "outbound arrival time + return departure time" to construct the hotel query window, and then lets the hotel agent search for matching hotels.

Inside the hotel agent, it is also "receive task -> call hotel tool -> return candidates."
The hotel tool performs city matching and time-window filtering to ensure the plan is feasible in time.

## Step 6: result aggregation and fallback handling.
The orchestrator assembles flights and hotels into combined options in a unified way, forming a data structure that the frontend can render directly.
There are several key fallback logics here:

Use one-way as a placeholder for one-way trips to avoid an empty page structure
Use no hotel match as a placeholder when there is no matching hotel
Construct a unified structure for hotel_only, ensuring the frontend does not need to write three sets of rendering logic
The value of this step is: "No matter how matching turns out, the output structure is stable."

## Step 7: natural language summary and return.
The last node is the summary node.
It reads structured candidates and generates a summary that users can read directly, such as:

How many groups of plans were found
The rough characteristics of each group
Recommend what the user should do next, such as filtering by price or confirming a specific plan
The final API returns three types of information:
Structured plans
Text summary
Intent type
At this point, one complete workflow is finished.