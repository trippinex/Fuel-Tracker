# FuelTrack

A lightweight web application for tracking vehicle fuel fill-ups, built with Flask + SQLite. Designed to run for free on Google Cloud Platform.

## Features

- **Vehicle management** — add and delete vehicles with tank capacity
- **Fill-up logging** — date, odometer, gallons, and price per gallon
- **Analytics dashboard** per vehicle:
  - Average / best / worst MPG
  - Total gallons, miles, and spend
  - Cost per mile, estimated range on a full tank
  - Average days and distance between fill-ups
  - MPG trend line chart + fuel volume/cost bar chart (Chart.js)

---

## Local Development

### Prerequisites

- Python 3.11+
- pip

### Setup

```bash
# 1. Clone / navigate to the project directory
cd "Fuel Tracker"

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the development server
FLASK_DEBUG=true python run.py
```

Open http://localhost:8080 in your browser.

The SQLite database is created automatically at `fuel_tracker.db` in the project root on first run.

---

## Docker (Local)

```bash
docker build -t fueltrack .

docker run -p 8080:8080 \
  -v $(pwd)/data:/data \
  fueltrack
```

Open http://localhost:8080. The database is persisted in `./data/fuel_tracker.db`.

---

## GCP Free Tier Deployment

Both options below stay within GCP's free tier limits as of 2024.

---

### Option A — Cloud Run + Filestore (simplest, serverless)

> **Note:** Cloud Run has no built-in persistent disk. For a zero-cost SQLite setup, mount a Cloud Filestore NFS share (1 TB NFS Basic HDD is free in some regions). Alternatively, swap SQLite for Cloud SQL (Postgres free tier) for a fully managed solution.

```bash
# 1. Set your project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable run.googleapis.com \
                       artifactregistry.googleapis.com

# 3. Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/fueltrack

# 4. Deploy (set SECRET_KEY to a random string)
gcloud run deploy fueltrack \
  --image gcr.io/YOUR_PROJECT_ID/fueltrack \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 256Mi \
  --set-env-vars SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  --set-env-vars DATABASE_PATH=/data/fuel_tracker.db
```

To persist the SQLite file across Cloud Run restarts, mount a Filestore NFS volume and point `DATABASE_PATH` at it. See the [Cloud Run filesystem docs](https://cloud.google.com/run/docs/configuring/services/nfs).

---

### Option B — Compute Engine e2-micro with persistent disk (recommended for SQLite)

This keeps SQLite on a persistent disk — the simplest, most reliable option.

```bash
# 1. Create a persistent disk (10 GB, well within free tier)
gcloud compute disks create fueltrack-data \
  --size=10GB \
  --zone=us-central1-a \
  --type=pd-standard

# 2. Create an e2-micro VM (free tier: 1 per month in us-central1/us-east1/us-west1)
gcloud compute instances create fueltrack-vm \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --disk=name=fueltrack-data,device-name=fueltrack-data,mode=rw \
  --tags=http-server \
  --metadata=startup-script='#!/bin/bash
    # Mount persistent disk
    mkdir -p /data
    if ! blkid /dev/disk/by-id/google-fueltrack-data; then
      mkfs.ext4 -F /dev/disk/by-id/google-fueltrack-data
    fi
    mount -o defaults /dev/disk/by-id/google-fueltrack-data /data
    echo "/dev/disk/by-id/google-fueltrack-data /data ext4 defaults 0 2" >> /etc/fstab

    # Install Docker
    curl -fsSL https://get.docker.com | sh

    # Pull and run the container
    docker pull gcr.io/YOUR_PROJECT_ID/fueltrack:latest
    docker run -d \
      --restart always \
      -p 80:8080 \
      -v /data:/data \
      -e SECRET_KEY=CHANGE_ME_TO_A_RANDOM_STRING \
      -e DATABASE_PATH=/data/fuel_tracker.db \
      gcr.io/YOUR_PROJECT_ID/fueltrack:latest
  '

# 3. Allow HTTP traffic
gcloud compute firewall-rules create allow-http \
  --allow=tcp:80 \
  --target-tags=http-server \
  --description="Allow HTTP to fueltrack"

# 4. Get the external IP
gcloud compute instances describe fueltrack-vm \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

Open `http://<EXTERNAL_IP>` in your browser.

#### Updating the app on the VM

```bash
gcloud compute ssh fueltrack-vm --zone=us-central1-a -- \
  "docker pull gcr.io/YOUR_PROJECT_ID/fueltrack:latest && \
   docker stop \$(docker ps -q) && \
   docker run -d --restart always -p 80:8080 \
     -v /data:/data \
     -e SECRET_KEY=CHANGE_ME \
     -e DATABASE_PATH=/data/fuel_tracker.db \
     gcr.io/YOUR_PROJECT_ID/fueltrack:latest"
```

---

## Environment Variables

| Variable              | Default                  | Required | Description                                                   |
|----------------------|--------------------------|----------|---------------------------------------------------------------|
| `SECRET_KEY`         | *(none)*                 | **Yes**  | Flask session secret. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. App refuses to start without it. |
| `GOOGLE_CLIENT_ID`   | *(none)*                 | **Yes**  | OAuth 2.0 client ID from Google Cloud Console                 |
| `GOOGLE_CLIENT_SECRET` | *(none)*               | **Yes**  | OAuth 2.0 client secret from Google Cloud Console             |
| `ALLOWED_EMAIL`      | *(none — open access)*   | No       | If set, only this Google account email is permitted to sign in |
| `DATABASE_PATH`      | `<cwd>/fuel_tracker.db`  | No       | Absolute path to the SQLite file                              |
| `PHOTOS_PATH`        | `/var/lib/fueltrack/photos` | No    | Directory where vehicle photos are stored                     |
| `PORT`               | `8080`                   | No       | Port the server listens on                                    |
| `FLASK_DEBUG`        | `false`                  | No       | Enable debug mode (dev only — never use in production)        |

---

## Project Structure

```
Fuel Tracker/
├── app/
│   ├── __init__.py             # Flask app factory, security headers, CSRF
│   ├── database.py             # SQLAlchemy instance
│   ├── models.py               # User, Vehicle, FillUp models
│   ├── routes/
│   │   ├── main.py             # Dashboard
│   │   ├── auth.py             # Google OAuth login / logout
│   │   ├── vehicles.py         # Vehicle CRUD + photo upload
│   │   ├── fillups.py          # Fill-up logging + history
│   │   ├── analytics.py        # Metrics + chart data (cached)
│   │   └── settings.py         # Account settings, backup/restore
│   ├── static/
│   │   ├── manifest.json       # PWA manifest
│   │   └── icons/              # App icons (192px, 512px, nav, 180px)
│   └── templates/
│       ├── base.html           # Shared layout (Tailwind CSS)
│       ├── login.html          # Google sign-in page
│       ├── index.html          # Dashboard
│       ├── vehicles.html       # Vehicle list
│       ├── add_vehicle.html    # Add vehicle form
│       ├── edit_vehicle.html   # Edit vehicle form
│       ├── fillup.html         # Log fill-up form
│       ├── fillups_history.html # Full fill-up history
│       ├── analytics.html      # Analytics + Chart.js
│       └── settings.html       # Account settings + backup/restore
├── run.py                      # Entry point
├── requirements.txt
├── Dockerfile
└── README.md
```
