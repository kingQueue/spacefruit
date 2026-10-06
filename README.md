# SpaceFruit Farming Robot Python Demo

This is a simulation-first prototype of the farming robot workflow.

## Promotional website

The cozy, garden-themed SpaceFruit introduction page is available at `/promo.html` when the frontend server is running. It includes an accessible video-demo placeholder ready to be replaced with recorded footage and a link back to the interactive garden app.

```bash
cd frontend
npm install
npm run dev
```

## Current workflow

1. Wait for start button.
2. Establish startup location as `(0, 0)`.
3. Simulate mapping a rectangular plot.
4. Read:
   - temperature
   - humidity
   - GPS latitude/longitude
   - current date/month
5. Generate crop recommendations.
6. Wait for confirmation through a local browser app.
7. Divide the plot into crop-specific spacing cells.
8. Ask the user to load seeds.
9. Simulate planting every seed.
10. Report completion.

## Run

Python 3.10+ is recommended.

```bash
python3 main.py
```

Press ENTER when prompted to simulate the physical start button.

Then open:

http://127.0.0.1:8080

Use the browser controls to:

1. Confirm the crop plan.
2. Simulate loading the seeds.

The robot will then execute the simulated planting sequence.

## Accounts and Supabase setup

Supabase Auth handles email/password sign-in, Google OAuth, sessions, and password resets. Supabase Postgres stores profiles, gardens, memberships, plots, harvest inventory, and marketplace listings. Install backend dependencies:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the Supabase project URL and publishable key. Never put a Supabase secret/service-role key in this app or its frontend. Start the Django API and Vite frontend in separate terminals:

```bash
python main.py
```

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Users can create an account from the sign-in screen. Supabase sends confirmation and password-reset emails; configure a custom SMTP provider in Supabase Auth before relying on email delivery outside the Supabase organization team.

Add `http://127.0.0.1:5173/**` to Supabase Auth's allowed redirect URLs. To enable Google sign-in, configure Google as a provider in Supabase Auth with OAuth credentials from Google Cloud; use the callback URL shown in Supabase's Google provider settings. Email/password and password-reset flows use Supabase Auth.

The initial Supabase schema is in `supabase/migrations/20261006000000_initial_schema.sql`. It enables RLS on the app tables and creates a private starter garden for each new Supabase Auth user. The app syncs plot and harvest summaries and stores marketplace listings in Supabase. Robot simulation state remains in process memory, so the active robot workflow resets when the backend restarts.

## Architecture

```text
                         Python application
                                |
        +-----------------------+-----------------------+
        |                       |                       |
    Sensor layer          Planning layer           App API
        |                       |                       |
   +----+-----+          +------+-------+         HTTP/JSON
   |          |          |              |
  GPS       BME280    Recommender     Grid planner
   |          |          |              |
   +----------+----------+--------------+
                         |
                     Robot state
                         |
                      Planter
```

## Important design decision

The hardware classes are intentionally separated from the robot state machine.

Later, replace:

- `StartButton`
- `TemperatureHumiditySensor`
- `GPSSensor`
- `PlotMapper`
- `Planter`

with real Raspberry Pi/MCU implementations.

The rest of the application can remain largely unchanged.

## Planned real hardware architecture

```text
Raspberry Pi 5
|
+-- Python / ROS 2
|   |
|   +-- App communication
|   +-- GPS/GNSS
|   +-- Environmental sensors
|   +-- Camera / computer vision
|   +-- Plot mapping
|   +-- Crop planning
|   +-- High-level navigation
|
+-- UART / USB / CAN
    |
    v
ESP32-S3 / STM32
|
+-- Motor control
+-- Encoder feedback
+-- PID loops
+-- Seed dispenser
+-- Limit switches
+-- Safety interlocks
```

## Safety

This demo does not drive real motors or planting hardware.

Before connecting real hardware, add:

- emergency stop
- motor current limits
- hardware limit switches
- obstacle detection
- watchdogs
- manual override
- seed-dispensing fault detection
- safe startup state
- authentication for remote commands
- authenticated/encrypted network communication
