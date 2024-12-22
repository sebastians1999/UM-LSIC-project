# IMPORTS

# Import the VPC Network
import {
    id = "projects/lsit-tutorapp/global/networks/lsit-network"
    to = google_compute_network.lsit-network
}

# Import the Cloud Run service
import {
    id = "locations/europe-west1/namespaces/lsit-tutorapp/services/fastapi-app"
    to = google_cloud_run_service.default
}

# Import the Redis instance
import {
    id = "projects/lsit-tutorapp/locations/europe-west1/instances/tutorapp"
    to = google_redis_instance.redis_instance
}

# Import the serverless connector
import {
    id = "projects/lsit-tutorapp/locations/europe-west1/connectors/serverless-connector"
    to = google_vpc_access_connector.serverless_connector
}

# Import the Cloud SQL Database
import {
    id = "projects/lsit-tutorapp/instances/tutorapp-db/databases/tutoring-app-production"
    to = google_sql_database.tutorapp_db
}

# Import the Cloud SQL Database Instance
import {
    id = "projects/lsit-tutorapp/instances/tutorapp-db"
    to = google_sql_database_instance.postgres_instance
}

# Access the database password from Google Secret Manager
data "google_secret_manager_secret_version" "db_password" {
    secret = "DATABASE_PASSWORD"
}

# Create SQL Database Instance
resource "google_sql_database_instance" "postgres_instance" {
    database_version = "POSTGRES_16"
    region = "europe-west1"

    settings {
        tier = "db-f1-micro"
        
        ip_configuration {
            private_network = google_compute_network.lsit-network.id
        }
    }
}

# Create SQL Database
resource "google_sql_database" "tutorapp_db" {
    name = "tutorapp_db"
    instance = google_sql_database_instance.postgres_instance.name
}

# Create Database User
resource "google_sql_user" "db_user" {
    name = "db_user"
    instance = google_sql_database_instance.postgres_instance.name
    password = data.google_secret_manager_secret_version.db_password.secret_data
}

# Create Compute Network
resource "google_compute_network" "lsit-network" {
    name = "lsit-network"
    auto_create_subnetworks = true

}

# Create Redis Instance
resource "google_redis_instance" "redis_instance" {
    name = "tutorapp"
    tier = "BASIC"
    memory_size_gb = 2
    region = "europe-west1"
    redis_version = "REDIS_6_X"
}

# Create VPC Access Connector
resource "google_vpc_access_connector" "serverless_connector" {
  name    = "serverless-connector"
  region  = "europe-west1"
  network = google_compute_network.lsit-network.id
  ip_cidr_range = "10.8.0.0/28"
  max_throughput = 300
  min_throughput = 200
}

# Create Cloud Run Service
resource "google_cloud_run_service" "default" {
    name     = "fastapi-app" # Name of the Cloud Run Service
    location = "europe-west1"

    metadata {
        namespace = "lsit-tutorapp" # Project ID
    }

    template {
        metadata {
            annotations = {
                "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.serverless_connector.id
                "egress" = "ALL_TRAFFIC"
            }
        }
        spec {
            timeout_seconds = 300
            containers {
                image = "gcr.io/lsit-tutorapp/fastapi-app:latest"

                # SET THE ENVIRONMENT VARIABLES
                env {
                    name = "REDIS_HOST"
                    value = google_redis_instance.redis_instance.host
                }

                env {
                    name = "REDIS_PORT"
                    value = 6379
                }

                env {
                    name = "GITLAB_CLIENT_ID"
                    value = "830223bc5b3f77464d6f6a8ed40c53f999f0283fca8f1e4c2ca39f5f0bb93262"
                }

                env {
                    name = "GITLAB_CLIENT_SECRET"
                    value_from {
                        secret_key_ref {
                            name = "GITLAB_CLIENT_SECRET"
                            key = "latest"
                        }
                    }
                }

                env {
                    name = "SECRET_KEY"
                    value_from {
                        secret_key_ref {
                            name = "SECRET_KEY"
                            key = "latest"
                        }
                    }
                }

                env {
                    name = "DB_PASSWORD"
                    value_from {
                        secret_key_ref {
                            name = "DATABASE_PASSWORD"
                            key = "latest"
                        }
                    }
                }

                env {
                    name = "DB_USER"
                    value = google_sql_user.db_user.name
                }

                env {
                    name = "DB_NAME"
                    value = google_sql_database.tutorapp_db.name
                }

                env {
                    name = "CLOUD_SQL_CONNECTION_NAME"
                    value = google_sql_database_instance.postgres_instance.connection_name
                }
            }
        }
    }

    traffic {
        percent         = 100
        latest_revision = true
    }
}


output "redis_host" {
 description = "The IP address of the redis memorystore instance."
 value = "${google_redis_instance.redis_instance.host}"
}

output "cloud_run_url" {
    description = "The URL of the deployed Cloud Run service"
    value       = google_cloud_run_service.default.status[0].url
}