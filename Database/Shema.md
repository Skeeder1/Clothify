Enum "job_status" {
    "pending"
    "processing"
    "done"
    "error"
    "sent"
}

Enum "garment_type" {
    "echarpe"
    "pull"
    "tshirt"
    "chemise"
    "veste"
    "manteau"
    "pantalon"
    "jean"
    "short"
    "jupe"
    "robe"
    "bonnet"
    "casquette"
    "sac"
    "other"
}

Enum "size_code" {
    "1"
    "2"
    "3"
    "4"
}

Table "public"."users" {
  "id" uuid [pk, default: `uuid_generate_v4()`]
  "discord_id" varchar(20) [unique, not null]
  "discord_name" varchar(100)
  "created_at" timestamp [default: `NOW()`]
  "last_seen_at" timestamp [default: `NOW()`]
  "total_jobs" integer [default: 0]
  "is_active" boolean [default: true]

  Indexes {
    discord_id [name: "idx_users_discord_id"]
  }
}

Table "public"."jobs" {
  "id" uuid [pk, default: `uuid_generate_v4()`]
  "user_id" uuid [ref: < "public"."users"."id"]
  "discord_message_id" varchar(20)
  "custom_prompt" text
  "input_file_paths" text [not null]
  "output_file_path" text
  "product_name" varchar(255)
  "garment" garment_type [default: `other`]
  "size" size_code [default: 2]
  "status" job_status [default: `pending`]
  "created_at" timestamp [default: `NOW()`]
  "started_at" timestamp
  "completed_at" timestamp

  Indexes {
    status [name: "idx_jobs_status"]
    user_id [name: "idx_jobs_user_id"]
    created_at [name: "idx_jobs_created_at"]
  }
}

Table "public"."job_logs" {
  "job_id" uuid [ref: < "public"."jobs"."id"]
  "id" serial [pk, not null, increment]
  "status" job_status [not null]
  "message" text
  "created_at" timestamp [default: `NOW()`]

  Indexes {
    job_id [name: "idx_job_logs_job_id"]
  }
}
