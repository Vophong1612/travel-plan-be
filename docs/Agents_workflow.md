graph TD
    A[User Query] --> B{Orchestrator};

    B -- Phase 1: Information Gathering (New Plan) --> C[User Intent Agent];
    C -- Extracts: Destination, Duration, Dates, Preferences (Food, Activities, POI), Travelers, Transportation Style --> D[TravelContext];

    D -- Pass Context --> E[Location & Weather Agent];
    E1[Google Maps API] -- Uses: google_maps MCP (Location Validation) --> E;
    E2[OpenWeather API] -- Uses: OpenWeatherAPI MCP (Weather Forecast) --> E;
    E -- Updates: Validated Location Details, Weather Data --> F[TravelContext Enriched];

    F -- Pass Context --> G[POI & Activity Agent];
    G1[Google Maps API] -- Uses: google_maps MCP, TripAdvisor MCP (POI/Activity Discovery, Details, Ratings) --> G;
    G2[TripAdvisor API] -- and --> G1;
    G -- Updates: Potential POIs, Potential Activities --> H[TravelContext with POIs/Activities];

    H -- Pass Context --> I[Food Recommendation Agent];
    I1[Google Maps API] -- Uses: google_maps MCP, TripAdvisor MCP (Restaurant Discovery, Details, Ratings) --> I;
    I2[TripAdvisor API] -- and --> I1;
    I -- Updates: Potential Restaurants --> J[TravelContext with Restaurants];

    J -- Phase 2: Plan Generation --> K[Itinerary Generation Agent];
    K1[Google Maps API] -- Uses: google_maps MCP (Travel Times, Optimization) --> K;
    K -- Organizes: POIs, Activities, Restaurants; Considers Weather, Travel Times --> L[TravelContext Proposed Itinerary];

    L -- Phase 3: Budget Estimation --> M[Budget Estimation Agent];
    M -- Calculates: Daily & Total Costs (using Price Ranges from TripAdvisor, Transportation Estimates from Google Maps, Multiplied by Travelers) --> N[TravelContext Estimated Budget];

    N -- Phase 4: Output Formatting --> O[Output Formatting Agent];
    O -- Formats: Final JSON Response (including Markdown Message, Trip Details, Extracted Info) --> P[Backend /chat Endpoint JSON Output];

    P -- User Feedback / Update Request --> B;

    subgraph Update Handling
        B -- Phase 5: Plan Adjustment (on Update Request) --> Q[Orchestrator - Update Logic];
        Q -- Parses Intent (Add/Remove/Replace) --> R[Identify Affected Components];
        R -- Re-evaluate POIs/Activities/Food --> G;
        R -- Re-organize Itinerary --> K;
        R -- Re-estimate Budget --> M;
    end

    G -- Updated Context for Update --> H;
    I -- Updated Context for Update --> J;
    K -- Updated Context for Update --> L;
    M -- Updated Context for Update --> N;

    N -- Re-format Output for Update --> O;
