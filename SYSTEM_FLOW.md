# System Flow Diagram - Outwit the AI Pirate Game

## Pełny przepływ systemu

```mermaid
flowchart TD
    Start([Użytkownik w Streamlit]) --> Input[Wprowadza wiadomość]
    Input --> Frontend[frontend/app.py<br/>send_message]
    
    Frontend --> API[POST /api/game/conversation<br/>FastAPI Backend]
    
    API --> PirateService[PirateService<br/>process_conversation]
    
    PirateService --> Detect[Wykryj Personę/Strategię<br/>_detect_persona<br/>_detect_strategy]
    Detect --> UpdateState[Aktualizuj GameState<br/>- Dodaj personę/strategię<br/>- Dodaj wiadomość do historii]
    
    UpdateState --> LangGraph[ConversationGraph<br/>process_message]
    
    LangGraph --> InitState[Inicjalizuj ConversationState<br/>- game_id<br/>- difficulty<br/>- conversation_history<br/>- strategies_attempted<br/>- player_personas]
    
    InitState --> MeritNode[Node: merit_check<br/>_merit_check_node]
    
    MeritNode --> MeritService[MeritCheckService<br/>evaluate_merit]
    
    MeritService --> FormatConv[Formatuj konwersację<br/>_format_conversation]
    FormatConv --> BuildPrompt[Zbuduj prompt oceny<br/>_build_evaluation_prompt]
    BuildPrompt --> LLMEval[OpenRouterService<br/>generate_response<br/>Model: gpt-4o-mini]
    
    LLMEval --> ParseEval[Parsuj odpowiedź JSON<br/>_parse_llm_evaluation]
    ParseEval --> CalcScore{Oblicz wynik<br/>decepcji}
    
    CalcScore -->|Sukces| SetMerit[Ustaw merit_score<br/>i merit_has_earned_it]
    CalcScore -->|Błąd| Fallback[Fallback Evaluation<br/>_fallback_evaluation]
    Fallback --> SetMerit
    
    SetMerit --> GenerateNode[Node: generate_response<br/>_generate_response_node]
    
    GenerateNode --> GetConfig[Pobierz konfigurację<br/>trudności]
    GetConfig --> BuildSystemPrompt[Zbuduj system prompt<br/>_build_system_prompt<br/>- Base prompt<br/>- Merit-based instruction<br/>- Forbidden phrase warning]
    
    BuildSystemPrompt --> FormatMessages[Formatuj wiadomości<br/>- System prompt<br/>- Historia konwersacji<br/>- Mapuj role: pirate→assistant]
    
    FormatMessages --> LLMGenerate[OpenRouterService<br/>generate_response<br/>Model: gpt-3.5/4o-mini/4-turbo]
    
    LLMGenerate --> ValidateNode[Node: validate_response<br/>_validate_response_node]
    
    ValidateNode --> CheckPhrase{Sprawdź zakazaną<br/>frazę}
    CheckPhrase -->|Zawiera| CheckScore1{Score >=<br/>threshold?}
    CheckPhrase -->|Nie zawiera| CheckAgreement{Sprawdź zgodę<br/>na skarb}
    
    CheckAgreement -->|Zgoda| CheckScore2{Score >=<br/>threshold-5?}
    CheckAgreement -->|Brak zgody| CheckScore3{Score >=<br/>threshold?}
    
    CheckScore1 -->|Tak| AllowPhrase[Pozwól frazę<br/>is_won = True]
    CheckScore1 -->|Nie| BlockPhrase[Zablokuj frazę<br/>_generate_alternative]
    
    CheckScore2 -->|Tak| AllowAgreement[Pozwól zgodę<br/>is_won = True]
    CheckScore2 -->|Nie| AllowResponse[Pozwól odpowiedź]
    
    CheckScore3 -->|Tak| SetWin[Ustaw is_won = True]
    CheckScore3 -->|Nie| AllowResponse
    
    BlockPhrase --> ReplaceResponse[Zastąp odpowiedź<br/>alternatywną]
    AllowPhrase --> CheckBlocked{is_blocked?}
    AllowAgreement --> CheckBlocked
    SetWin --> CheckBlocked
    AllowResponse --> CheckBlocked
    ReplaceResponse --> CheckBlocked
    
    CheckBlocked -->|Blocked| HandleBlocked[Node: handle_blocked<br/>_handle_blocked_node]
    CheckBlocked -->|Allowed| ReturnState[Zwróć final_state]
    
    HandleBlocked --> ReturnState
    
    ReturnState --> UpdateGameState[Aktualizuj GameState<br/>- merit_score<br/>- conversation_history<br/>- is_won]
    
    UpdateGameState --> CheckAudio{include_audio?}
    
    CheckAudio -->|Tak| ElevenLabs[ElevenLabsService<br/>generate_speech<br/>via Kie.ai API]
    CheckAudio -->|Nie| BuildResponse[Zbuduj ConversationResponse]
    
    ElevenLabs --> CreateTask[Utwórz zadanie TTS<br/>create_tts_task]
    CreateTask --> PollStatus[Sprawdź status<br/>get_task_status]
    PollStatus -->|Pending| Wait[Oczekaj 2s]
    Wait --> PollStatus
    PollStatus -->|Success| GetAudioURL[Pobierz URL audio]
    PollStatus -->|Failed| BuildResponse
    
    GetAudioURL --> BuildResponse
    
    BuildResponse --> ReturnAPI[Zwróć do API]
    ReturnAPI --> FrontendResponse[Streamlit otrzymuje<br/>odpowiedź]
    
    FrontendResponse --> UpdateUI[Aktualizuj UI<br/>- Dodaj do historii<br/>- Zaktualizuj score<br/>- Pokaż audio jeśli dostępne]
    
    UpdateUI --> End([Wyświetl odpowiedź<br/>użytkownikowi])
    
    style MeritNode fill:#e1f5ff
    style GenerateNode fill:#fff4e1
    style ValidateNode fill:#ffe1f5
    style LLMEval fill:#e1ffe1
    style LLMGenerate fill:#e1ffe1
    style ElevenLabs fill:#ffe1e1
```

## Architektura systemu

```mermaid
graph TB
    subgraph Frontend["Frontend Layer"]
        Streamlit[Streamlit App<br/>frontend/app.py]
    end
    
    subgraph API["API Layer"]
        FastAPI[FastAPI Server<br/>backend/main.py]
        Endpoints["Endpoints:<br/>POST /api/game/start<br/>POST /api/game/conversation<br/>GET /api/game/{game_id}"]
    end
    
    subgraph Services["Service Layer"]
        PirateService[PirateService<br/>Orchestracja]
        ConversationGraph[ConversationGraph<br/>LangGraph State Machine]
        MeritService[MeritCheckService<br/>Ocena decepcji]
        ValidationService[ValidationService<br/>Walidacja odpowiedzi]
        OpenRouterService[OpenRouterService<br/>LLM API]
        ElevenLabsService[ElevenLabsService<br/>TTS via Kie.ai]
    end
    
    subgraph External["External Services"]
        OpenRouter[OpenRouter API<br/>gpt-3.5/4o-mini/4-turbo]
        KieAI[Kie.ai API<br/>ElevenLabs TTS]
    end
    
    subgraph Data["Data Layer"]
        GameState[GameState<br/>- game_id<br/>- difficulty<br/>- conversation_history<br/>- merit_score<br/>- player_personas<br/>- strategies_attempted]
        Config[Config<br/>DIFFICULTY_LEVELS<br/>FORBIDDEN_PHRASE]
    end
    
    Streamlit -->|HTTP REST| FastAPI
    FastAPI --> Endpoints
    Endpoints --> PirateService
    
    PirateService --> ConversationGraph
    PirateService --> ValidationService
    PirateService --> ElevenLabsService
    
    ConversationGraph --> MeritService
    ConversationGraph --> OpenRouterService
    ConversationGraph --> ValidationService
    
    MeritService --> OpenRouterService
    OpenRouterService --> OpenRouter
    
    ElevenLabsService --> KieAI
    
    PirateService --> GameState
    ConversationGraph --> Config
    MeritService --> Config
    ValidationService --> Config
    
    style Frontend fill:#e3f2fd
    style API fill:#f3e5f5
    style Services fill:#e8f5e9
    style External fill:#fff3e0
    style Data fill:#fce4ec
```

## LangGraph State Machine - Szczegóły

```mermaid
stateDiagram-v2
    [*] --> merit_check: User Message
    
    state merit_check {
        [*] --> FormatConversation
        FormatConversation --> BuildPrompt
        BuildPrompt --> CallLLM
        CallLLM --> ParseResponse
        ParseResponse --> CalculateScore
        CalculateScore --> [*]
    }
    
    merit_check --> generate_response: merit_score set
    
    state generate_response {
        [*] --> GetDifficultyConfig
        GetDifficultyConfig --> BuildSystemPrompt
        BuildSystemPrompt --> FormatMessages
        FormatMessages --> CallLLM
        CallLLM --> [*]
    }
    
    generate_response --> should_validate: Response generated
    
    should_validate --> validate_response: Always validate
    should_validate --> [*]: Skip (never)
    
    state validate_response {
        [*] --> CheckForbiddenPhrase
        CheckForbiddenPhrase --> CheckAgreement
        CheckAgreement --> CheckScore
        CheckScore --> SetWinCondition
        SetWinCondition --> [*]
    }
    
    validate_response --> is_response_allowed: Validation complete
    
    is_response_allowed --> [*]: Allowed
    is_response_allowed --> handle_blocked: Blocked
    
    handle_blocked --> [*]: Alternative response set
    
    [*] --> [*]: Return final_state
```

## Warunki wygranej (Win Conditions)

```mermaid
flowchart TD
    Start[Odpowiedź pirata] --> CheckExact{Contains exact<br/>forbidden phrase?}
    
    CheckExact -->|Yes| CheckScore1{Score >=<br/>threshold?}
    CheckExact -->|No| CheckAgreement{Contains treasure<br/>agreement?}
    
    CheckScore1 -->|Yes| Win1[WIN: Exact phrase<br/>+ High score]
    CheckScore1 -->|No| Block[BLOCK: Replace with<br/>alternative]
    
    CheckAgreement -->|Yes| CheckScore2{Score >=<br/>threshold-5?}
    CheckAgreement -->|No| CheckScore3{Score >=<br/>threshold?}
    
    CheckScore2 -->|Yes| Win2[WIN: Agreement<br/>+ Close score]
    CheckScore2 -->|No| Allow[ALLOW: Normal response]
    
    CheckScore3 -->|Yes| Win3[WIN: High score<br/>regardless of phrase]
    CheckScore3 -->|No| Allow
    
    Win1 --> End([Player Wins!])
    Win2 --> End
    Win3 --> End
    Block --> End
    Allow --> End
    
    style Win1 fill:#4caf50
    style Win2 fill:#4caf50
    style Win3 fill:#4caf50
    style Block fill:#ff9800
    style Allow fill:#2196f3
```

## Ocena decepcji (Deception Evaluation)

```mermaid
flowchart LR
    Input[Conversation History<br/>Strategies<br/>Personas] --> LLM[LLM Evaluation<br/>gpt-4o-mini]
    
    LLM --> Parse[Parse JSON Response]
    
    Parse --> Scores[Deception Scores:<br/>- total_score: 0-100<br/>- strategy_variety: 0-30<br/>- conversation_depth: 0-25<br/>- creativity: 0-25<br/>- persistence: 0-20]
    
    Scores --> Compare{Compare with<br/>threshold}
    
    Compare -->|Score >= threshold| HighScore[merit_has_earned_it = True<br/>Pirate more vulnerable]
    Compare -->|Score < threshold| LowScore[merit_has_earned_it = False<br/>Pirate suspicious]
    
    HighScore --> Result[Return MeritEvaluation]
    LowScore --> Result
    
    style HighScore fill:#4caf50
    style LowScore fill:#f44336
```

## Przykładowe wzorce zgody na skarb

System wykrywa następujące wzorce jako zgodę pirata na oddanie skarbu:

- `"tak, skarb jest teraz twój"`
- `"skarb jest twój"`
- `"skarb należy do ciebie"`
- `"daję ci mój skarb"`
- `"weź go"` (w kontekście skarbu)
- `"skarb jest już twój"`

Jeśli którykolwiek z tych wzorców zostanie wykryty I wynik decepcji jest wystarczająco wysoki (lub bliski progu), gracz wygrywa.



