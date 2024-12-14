resource "google_cloud_run_service" "default" {
    name     = "fastapi-app" # Name of the Cloud Run Service
    location = "europe-west1"

    metadata {
        namespace = "lsit-tutorapp" # Project ID
    }

    template {
        spec {
            containers {
                image = "gcr.io/lsit-tutorapp/fastapi-app:latest"

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
            }

            metadata {
                labels = {
                    "last-deployed" = timestamp() # This will force a new revision
                }
            }
        }
    }

    traffic {
        percent         = 100
        latest_revision = true
    }
}

import {
    id = "locations/europe-west1/namespaces/lsit-tutorapp/services/fastapi-app"
    to = google_cloud_run_service.default
}


output "cloud_run_url" {
    description = "The URL of the deployed Cloud Run service"
    value       = google_cloud_run_service.default.status[0].url
}