# Scoring System & LangGraph Flow - Detailed Explanation

## How Points Are Added - Complete Flow

```mermaid
flowchart TD
    Start([User Sends Message]) --> Detect[PirateService: Detect Persona/Strategy<br/>_detect_persona<br/>_detect_strategy]
    
    Detect --> CheckPersona{New Persona<br/>Detected?}
    CheckPersona -->|Yes| AddPersona[Add to player_personas<br/>e.g. 'crew_member', 'merchant']
    CheckPersona -->|No| CheckStrategy
    
    AddPersona --> CheckStrategy{New Strategy<br/>Detected?}
    CheckStrategy -->|Yes| AddStrategy[Add to strategies_attempted<br/>e.g. 'deception', 'false_identity']
    CheckStrategy -->|No| AddMessage
    
    AddStrategy --> AddMessage[Add User Message<br/>to conversation_history]
    
    AddMessage --> LangGraph[LangGraph: process_message<br/>Starts State Machine]
    
    LangGraph --> InitState[Initialize ConversationState<br/>merit_score = 0<br/>merit_has_earned_it = False]
    
    InitState --> MeritNode[Node 1: merit_check<br/>_merit_check_node]
    
    MeritNode --> FormatConv[Format Conversation<br/>Last 15 messages<br/>Format: 'Gracz: ...' / 'Pirat: ...']
    
    FormatConv --> BuildPrompt[Build Evaluation Prompt<br/>Include:<br/>- Conversation text<br/>- Strategies attempted<br/>- Player personas<br/>- Difficulty level]
    
    BuildPrompt --> LLMEval[Call LLM for Evaluation<br/>Model: gpt-4o-mini<br/>Temperature: 0.3<br/>Prompt: Analyze deception level]
    
    LLMEval --> ParseJSON[Parse LLM JSON Response<br/>Extract scores:<br/>- total_score: 0-100<br/>- strategy_variety: 0-30<br/>- conversation_depth: 0-25<br/>- creativity: 0-25<br/>- persistence: 0-20]
    
    ParseJSON --> ValidateScores{Valid<br/>JSON?}
    
    ValidateScores -->|Yes| SetScores[Set State Scores<br/>state['merit_score'] = total_score<br/>state['merit_has_earned_it'] = score >= threshold]
    ValidateScores -->|No| Fallback[Fallback Evaluation<br/>Calculate based on:<br/>- unique_strategies × 5<br/>- unique_personas × 3<br/>- conversation_length × 2]
    
    Fallback --> SetScores
    
    SetScores --> GenerateNode[Node 2: generate_response<br/>_generate_response_node]
    
    GenerateNode --> GetConfig[Get Difficulty Config<br/>Model: gpt-3.5/4o-mini/4-turbo<br/>System prompt template]
    
    GetConfig --> BuildSystemPrompt[Build System Prompt<br/>Include merit_has_earned_it<br/>If True: 'Be more vulnerable'<br/>If False: 'Be suspicious']
    
    BuildSystemPrompt --> FormatMessages[Format Messages for LLM<br/>- System prompt<br/>- Last 10 conversation messages<br/>- Map roles: pirate→assistant]
    
    FormatMessages --> LLMGenerate[Call LLM for Response<br/>Generate pirate's reply]
    
    LLMGenerate --> ValidateNode[Node 3: validate_response<br/>_validate_response_node]
    
    ValidateNode --> CheckWin[Check Win Conditions<br/>Based on:<br/>- merit_score<br/>- Forbidden phrase<br/>- Treasure agreement]
    
    CheckWin --> ReturnState[Return Final State<br/>merit_score<br/>pirate_response<br/>is_won]
    
    ReturnState --> UpdateGame[Update GameState<br/>game_state.merit_score = result['merit_score']]
    
    UpdateGame --> ReturnResponse[Return ConversationResponse<br/>to Frontend]
    
    style MeritNode fill:#e1f5ff
    style SetScores fill:#4caf50
    style LLMEval fill:#fff4e1
    style ParseJSON fill:#fff4e1
    style UpdateGame fill:#4caf50
```

## Scoring Components - What Gets Evaluated

```mermaid
flowchart LR
    Input[Conversation Data] --> Components[Scoring Components]
    
    Components --> C1[Strategy Variety<br/>0-30 points<br/>Based on unique strategies:<br/>- deception<br/>- false_identity<br/>- manipulation<br/>- lies<br/>- trickery<br/>- flattery<br/>- emotional<br/>etc.]
    
    Components --> C2[Conversation Depth<br/>0-25 points<br/>Based on:<br/>- Length of conversation<br/>- Average message length<br/>- Engagement level]
    
    Components --> C3[Creativity<br/>0-25 points<br/>Based on:<br/>- Novel approaches<br/>- Unique stories<br/>- Creative lies<br/>- Emotional manipulation]
    
    Components --> C4[Persistence<br/>0-20 points<br/>Based on:<br/>- Attempts after refusals<br/>- Continued deception<br/>- Conversation length]
    
    C1 --> Total[Total Score<br/>0-100<br/>Sum of all components]
    C2 --> Total
    C3 --> Total
    C4 --> Total
    
    Total --> Threshold{Compare with<br/>Difficulty Threshold}
    
    Threshold -->|Easy: >= 40| EasyWin[merit_has_earned_it = True]
    Threshold -->|Medium: >= 60| MediumWin[merit_has_earned_it = True]
    Threshold -->|Hard: >= 80| HardWin[merit_has_earned_it = True]
    Threshold -->|Below threshold| LowScore[merit_has_earned_it = False]
    
    style Total fill:#4caf50
    style EasyWin fill:#81c784
    style MediumWin fill:#66bb6a
    style HardWin fill:#4caf50
    style LowScore fill:#ef5350
```

## When Points Are Added - Timeline

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant PirateService
    participant LangGraph
    participant MeritService
    participant LLM
    participant GameState
    
    User->>Frontend: Types message
    Frontend->>API: POST /api/game/conversation
    API->>PirateService: process_conversation()
    
    Note over PirateService: BEFORE LangGraph
    PirateService->>PirateService: Detect persona/strategy
    PirateService->>GameState: Add persona if new
    PirateService->>GameState: Add strategy if new
    PirateService->>GameState: Add user message to history
    
    Note over PirateService,LangGraph: LANGGRAPH STARTS
    PirateService->>LangGraph: process_message()
    
    Note over LangGraph: Node 1: merit_check
    LangGraph->>MeritService: evaluate_merit()
    MeritService->>MeritService: Format conversation (last 15 msgs)
    MeritService->>MeritService: Build evaluation prompt
    MeritService->>LLM: Request deception evaluation
    LLM-->>MeritService: JSON with scores
    MeritService->>MeritService: Parse JSON response
    MeritService->>MeritService: Calculate has_earned_it
    MeritService-->>LangGraph: MeritEvaluation object
    
    Note over LangGraph: POINTS SET HERE
    LangGraph->>LangGraph: state['merit_score'] = evaluation.total_score
    LangGraph->>LangGraph: state['merit_has_earned_it'] = evaluation.has_earned_it
    
    Note over LangGraph: Node 2: generate_response
    LangGraph->>LLM: Generate pirate response
    LLM-->>LangGraph: Pirate response text
    
    Note over LangGraph: Node 3: validate_response
    LangGraph->>LangGraph: Check win conditions
    LangGraph-->>PirateService: Final state with merit_score
    
    Note over PirateService: AFTER LangGraph
    PirateService->>GameState: Update merit_score
    PirateService->>GameState: Add pirate response to history
    PirateService->>GameState: Update is_won if applicable
    PirateService-->>API: ConversationResponse
    API-->>Frontend: Response with merit_score
    Frontend->>User: Display updated score
```

## Complete LangGraph State Machine Flow

```mermaid
stateDiagram-v2
    [*] --> InitialState: User Message Received
    
    state InitialState {
        game_id: string
        difficulty: string
        conversation_history: []
        strategies_attempted: []
        player_personas: []
        merit_score: 0
        merit_has_earned_it: false
        pirate_response: ""
        is_blocked: false
        is_won: false
    }
    
    InitialState --> MeritCheck: Entry Point
    
    state MeritCheck {
        [*] --> FormatConversation
        FormatConversation: Take last 15 messages
        FormatConversation --> BuildPrompt
        BuildPrompt: Include strategies, personas, difficulty
        BuildPrompt --> CallLLM
        CallLLM: gpt-4o-mini evaluation
        CallLLM --> ParseResponse
        ParseResponse: Extract JSON scores
        ParseResponse --> CalculateThreshold
        CalculateThreshold: Compare score vs threshold
        CalculateThreshold --> SetState
        SetState: merit_score = total_score
        SetState: merit_has_earned_it = (score >= threshold)
        SetState --> [*]
    }
    
    MeritCheck --> GenerateResponse: Always proceed
    
    state GenerateResponse {
        [*] --> GetDifficultyConfig
        GetDifficultyConfig: Select model & prompt template
        GetDifficultyConfig --> BuildSystemPrompt
        BuildSystemPrompt: Include merit_has_earned_it status
        BuildSystemPrompt --> FormatMessages
        FormatMessages: Map roles, filter empty
        FormatMessages --> CallLLM
        CallLLM: Generate pirate response
        CallLLM --> [*]
    }
    
    GenerateResponse --> ShouldValidate: Response generated
    
    ShouldValidate --> ValidateResponse: Always validate
    ShouldValidate --> End: Skip (never happens)
    
    state ValidateResponse {
        [*] --> CheckForbiddenPhrase
        CheckForbiddenPhrase: Exact phrase match?
        CheckForbiddenPhrase --> CheckAgreement
        CheckAgreement: Treasure agreement patterns?
        CheckAgreement --> CheckScore
        CheckScore: Compare merit_score vs threshold
        CheckScore --> SetWinCondition
        SetWinCondition: Set is_won based on conditions
        SetWinCondition --> [*]
    }
    
    ValidateResponse --> IsResponseAllowed: Validation complete
    
    IsResponseAllowed --> End: Allowed (is_blocked = false)
    IsResponseAllowed --> HandleBlocked: Blocked (is_blocked = true)
    
    state HandleBlocked {
        [*] --> PassThrough
        PassThrough: Alternative already set
        PassThrough --> [*]
    }
    
    HandleBlocked --> End
    
    End --> [*]: Return final_state
```

## Detailed LangGraph Node Execution

```mermaid
flowchart TD
    Start([process_message called]) --> CreateState[Create ConversationState<br/>with initial values]
    
    CreateState --> InvokeGraph[graph.ainvoke initial_state]
    
    InvokeGraph --> Node1[Node 1: merit_check<br/>ASYNC]
    
    Node1 --> N1Step1[1. Get conversation_history<br/>from state]
    N1Step1 --> N1Step2[2. Get strategies_attempted<br/>from state]
    N1Step2 --> N1Step3[3. Get player_personas<br/>from state]
    N1Step3 --> N1Step4[4. Call MeritService.evaluate_merit]
    
    N1Step4 --> N1Step5[5. Format conversation<br/>Last 15 messages]
    N1Step5 --> N1Step6[6. Build evaluation prompt<br/>Include all context]
    N1Step6 --> N1Step7[7. Call LLM for evaluation<br/>gpt-4o-mini]
    N1Step7 --> N1Step8[8. Parse JSON response]
    N1Step8 --> N1Step9[9. Calculate threshold check]
    N1Step9 --> N1Step10[10. Update state:<br/>merit_score = total_score<br/>merit_has_earned_it = bool]
    
    N1Step10 --> Node2[Node 2: generate_response<br/>ASYNC]
    
    Node2 --> N2Step1[1. Get difficulty config]
    N2Step1 --> N2Step2[2. Get model name<br/>gpt-3.5/4o-mini/4-turbo]
    N2Step2 --> N2Step3[3. Build system prompt<br/>Based on merit_has_earned_it]
    N2Step3 --> N2Step4[4. Format messages<br/>System + last 10 messages]
    N2Step4 --> N2Step5[5. Map roles<br/>pirate → assistant]
    N2Step5 --> N2Step6[6. Call LLM for generation]
    N2Step6 --> N2Step7[7. Update state:<br/>pirate_response = response]
    
    N2Step7 --> Conditional1{_should_validate<br/>Always returns 'validate'}
    
    Conditional1 -->|validate| Node3[Node 3: validate_response<br/>SYNC]
    Conditional1 -->|skip| End[END - Never happens]
    
    Node3 --> N3Step1[1. Call ValidationService<br/>validate_response]
    N3Step1 --> N3Step2[2. Check forbidden phrase]
    N3Step2 --> N3Step3[3. Check treasure agreement]
    N3Step3 --> N3Step4[4. Get threshold for difficulty]
    N3Step4 --> N3Step5[5. Check win conditions:<br/>- Exact phrase + high score<br/>- Agreement + high score<br/>- Agreement + close score<br/>- High score alone]
    N3Step5 --> N3Step6[6. Update state:<br/>is_blocked = not is_allowed<br/>is_won = based on conditions]
    
    N3Step6 --> Conditional2{_is_response_allowed<br/>Check is_blocked}
    
    Conditional2 -->|allowed| End[END]
    Conditional2 -->|blocked| Node4[Node 4: handle_blocked<br/>SYNC]
    
    Node4 --> N4Step1[1. Pass through<br/>Alternative already set]
    N4Step1 --> End
    
    End --> Return[Return final_state<br/>to process_message]
    
    Return --> Extract[Extract from final_state:<br/>- pirate_response<br/>- merit_score<br/>- merit_has_earned_it<br/>- is_won<br/>- is_blocked]
    
    Extract --> Done([Return to PirateService])
    
    style Node1 fill:#e1f5ff
    style Node2 fill:#fff4e1
    style Node3 fill:#ffe1f5
    style Node4 fill:#f5e1ff
    style N1Step10 fill:#4caf50
    style N3Step6 fill:#4caf50
```

## Score Calculation - LLM Evaluation Process

```mermaid
flowchart TD
    Input[Input Data] --> Format[Format Conversation<br/>_format_conversation]
    
    Format --> BuildPrompt[Build Evaluation Prompt<br/>_build_evaluation_prompt]
    
    BuildPrompt --> PromptContent[Prompt Contains:<br/>1. Full conversation text<br/>2. Strategies attempted list<br/>3. Player personas list<br/>4. Difficulty level<br/>5. Scoring criteria]
    
    PromptContent --> LLMCall[Call LLM<br/>Model: gpt-4o-mini<br/>Temperature: 0.3<br/>Max tokens: 500]
    
    LLMCall --> LLMResponse[LLM Response<br/>JSON format]
    
    LLMResponse --> Parse[Parse JSON<br/>_parse_llm_evaluation]
    
    Parse --> Extract[Extract Scores:<br/>total_score: 0-100<br/>strategy_variety: 0-30<br/>conversation_depth: 0-25<br/>creativity: 0-25<br/>persistence: 0-20]
    
    Extract --> Validate{Valid<br/>Scores?}
    
    Validate -->|Yes| Clamp[Clamp to ranges<br/>min 0, max limits]
    Validate -->|No| Fallback[Use Fallback<br/>_fallback_evaluation]
    
    Fallback --> FallbackCalc[Calculate from:<br/>unique_strategies × 5<br/>unique_personas × 3<br/>conversation_length × 2<br/>etc.]
    
    FallbackCalc --> Clamp
    
    Clamp --> GetThreshold[Get Threshold<br/>from DIFFICULTY_LEVELS]
    
    GetThreshold --> Compare{total_score >=<br/>threshold?}
    
    Compare -->|Yes| HighScore[merit_has_earned_it = True<br/>Pirate becomes vulnerable]
    Compare -->|No| LowScore[merit_has_earned_it = False<br/>Pirate stays suspicious]
    
    HighScore --> Return[Return MeritEvaluation]
    LowScore --> Return
    
    Return --> StateUpdate[Update State<br/>merit_score = total_score<br/>merit_has_earned_it = bool]
    
    style LLMCall fill:#fff4e1
    style Extract fill:#4caf50
    style HighScore fill:#81c784
    style LowScore fill:#ef5350
    style StateUpdate fill:#4caf50
```

## Win Condition Logic - When Player Wins

```mermaid
flowchart TD
    Start[Pirate Response Generated] --> CheckExact{Contains Exact<br/>Forbidden Phrase?<br/>'Oto mój skarb, weź go'}
    
    CheckExact -->|Yes| CheckScore1{merit_score >=<br/>threshold?}
    CheckExact -->|No| CheckAgreement{Contains Treasure<br/>Agreement Pattern?<br/>e.g. 'skarb jest twój'}
    
    CheckScore1 -->|Yes| Win1[WIN: Exact phrase<br/>+ High score<br/>is_won = True]
    CheckScore1 -->|No| Block1[BLOCK: Replace with<br/>alternative response<br/>is_blocked = True]
    
    CheckAgreement -->|Yes| CheckScore2{merit_score >=<br/>threshold - 5?}
    CheckAgreement -->|No| CheckScore3{merit_score >=<br/>threshold?}
    
    CheckScore2 -->|Yes| Win2[WIN: Agreement<br/>+ Close score<br/>is_won = True]
    CheckScore2 -->|No| Allow1[ALLOW: Normal response<br/>is_won = False]
    
    CheckScore3 -->|Yes| Win3[WIN: High score<br/>regardless of phrase<br/>is_won = True]
    CheckScore3 -->|No| Allow2[ALLOW: Normal response<br/>is_won = False]
    
    Win1 --> End([Return State])
    Win2 --> End
    Win3 --> End
    Block1 --> End
    Allow1 --> End
    Allow2 --> End
    
    style Win1 fill:#4caf50
    style Win2 fill:#4caf50
    style Win3 fill:#4caf50
    style Block1 fill:#ff9800
    style Allow1 fill:#2196f3
    style Allow2 fill:#2196f3
```

## Key Points Summary

### When Points Are Added:
1. **Before LangGraph**: Personas and strategies are detected and added to GameState
2. **During LangGraph - Node 1 (merit_check)**: 
   - LLM evaluates the entire conversation
   - Calculates deception score (0-100)
   - Sets `merit_score` in state
   - Determines `merit_has_earned_it` (score >= threshold)
3. **After LangGraph**: 
   - `merit_score` is copied from state to GameState
   - Frontend receives updated score

### How Points Are Calculated:
- **LLM-based evaluation** (primary): Uses gpt-4o-mini to analyze conversation and return JSON with scores
- **Fallback evaluation** (if LLM fails): Rule-based calculation from strategies, personas, and conversation length
- **Components**: Strategy Variety (0-30) + Conversation Depth (0-25) + Creativity (0-25) + Persistence (0-20) = Total Score (0-100)

### LangGraph Flow:
1. **merit_check node** (async): Evaluates deception, sets score
2. **generate_response node** (async): Generates pirate response based on score
3. **validate_response node** (sync): Checks win conditions
4. **handle_blocked node** (sync): Handles blocked responses (if needed)

### Win Conditions:
- Exact forbidden phrase + high score
- Treasure agreement + high score  
- Treasure agreement + close score (within 5 points)
- High score alone (>= threshold)



