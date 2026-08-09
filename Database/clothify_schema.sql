--
-- PostgreSQL database dump
--

\restrict DrKZdoxQ4LxPrVWcOTmRMr3zb0pae2aIvBaDF1I5kYJ27whkiUYPtKutM72fk8U

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: garment_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.garment_type AS ENUM (
    'echarpe',
    'pull',
    'tshirt',
    'chemise',
    'veste',
    'manteau',
    'pantalon',
    'jean',
    'short',
    'jupe',
    'robe',
    'bonnet',
    'casquette',
    'sac',
    'other'
);


--
-- Name: job_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.job_status AS ENUM (
    'pending',
    'processing',
    'done',
    'error',
    'sent'
);


--
-- Name: size_code; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.size_code AS ENUM (
    '1',
    '2',
    '3',
    '4'
);


--
-- Name: complete_job(uuid, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.complete_job(p_job_id uuid, p_output_path text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  UPDATE jobs
  SET
    status = 'done',
    output_file_path = p_output_path,
    completed_at = NOW()
  WHERE id = p_job_id;
END;
$$;


--
-- Name: FUNCTION complete_job(p_job_id uuid, p_output_path text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.complete_job(p_job_id uuid, p_output_path text) IS 'Marks a job as successfully completed with output path';


--
-- Name: fail_job(uuid, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fail_job(p_job_id uuid, p_error_msg text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  v_attempts INTEGER;
  v_max_attempts INTEGER;
BEGIN
  SELECT attempts, max_attempts
  INTO v_attempts, v_max_attempts
  FROM jobs
  WHERE id = p_job_id;

  IF v_attempts >= v_max_attempts THEN
    -- Max attempts reached: permanent failure
    UPDATE jobs
    SET
      status = 'error',
      error_message = p_error_msg,
      completed_at = NOW()
    WHERE id = p_job_id;
  ELSE
    -- Still has retries: reset to pending
    UPDATE jobs
    SET
      status = 'pending',
      error_message = p_error_msg,
      started_at = NULL
    WHERE id = p_job_id;
  END IF;
END;
$$;


--
-- Name: FUNCTION fail_job(p_job_id uuid, p_error_msg text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.fail_job(p_job_id uuid, p_error_msg text) IS 'Marks a job as failed. Retries if attempts < max_attempts';


--
-- Name: get_queue_stats(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_queue_stats() RETURNS TABLE(pending_count integer, processing_count integer, done_count integer, error_count integer, oldest_pending timestamp without time zone)
    LANGUAGE sql
    AS $$
  SELECT
    (SELECT COUNT(*)::INTEGER FROM jobs WHERE status = 'pending'),
    (SELECT COUNT(*)::INTEGER FROM jobs WHERE status = 'processing'),
    (SELECT COUNT(*)::INTEGER FROM jobs WHERE status = 'done' AND completed_at > NOW() - INTERVAL '24 hours'),
    (SELECT COUNT(*)::INTEGER FROM jobs WHERE status = 'error' AND created_at > NOW() - INTERVAL '24 hours'),
    (SELECT MIN(created_at) FROM jobs WHERE status = 'pending');
$$;


--
-- Name: FUNCTION get_queue_stats(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.get_queue_stats() IS 'Returns queue statistics: pending, processing, done (24h), error (24h), oldest pending';


--
-- Name: notify_n8n_new_job(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.notify_n8n_new_job() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ begin perform pg_notify('n8n_jobs_channel', row_to_json(new)::text); return null; end; $$;


--
-- Name: reset_stale_jobs(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.reset_stale_jobs(timeout_minutes integer DEFAULT 5) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
  v_count INTEGER := 0;
BEGIN
  -- Reset jobs that can be retried
  WITH stale_retry AS (
    UPDATE jobs
    SET
      status = 'pending',
      error_message = 'Job timeout - will retry',
      started_at = NULL
    WHERE status = 'processing'
      AND started_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
      AND attempts < max_attempts
    RETURNING id
  )
  SELECT COUNT(*) INTO v_count FROM stale_retry;

  -- Mark as error jobs that exceeded max attempts
  WITH stale_error AS (
    UPDATE jobs
    SET
      status = 'error',
      error_message = 'Job timeout - max attempts reached',
      completed_at = NOW()
    WHERE status = 'processing'
      AND started_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
      AND attempts >= max_attempts
    RETURNING id
  )
  SELECT v_count + COUNT(*) INTO v_count FROM stale_error;

  RETURN v_count;
END;
$$;


--
-- Name: FUNCTION reset_stale_jobs(timeout_minutes integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.reset_stale_jobs(timeout_minutes integer) IS 'Resets jobs stuck in processing state based on started_at';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: job_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_logs (
    id integer NOT NULL,
    job_id uuid,
    status public.job_status NOT NULL,
    message text,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: job_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_logs_id_seq OWNED BY public.job_logs.id;


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jobs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    discord_message_id character varying(20),
    custom_prompt text,
    input_file_paths text NOT NULL,
    output_file_path text,
    product_name character varying(255),
    size public.size_code DEFAULT '2'::public.size_code,
    status public.job_status DEFAULT 'pending'::public.job_status,
    created_at timestamp without time zone DEFAULT now(),
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    attempts integer DEFAULT 0,
    max_attempts integer DEFAULT 3,
    error_message text,
    garment text DEFAULT 'other'::text NOT NULL,
    genre character varying(10),
    angle character varying(20),
    CONSTRAINT check_garment_length CHECK (((char_length(garment) >= 2) AND (char_length(garment) <= 50)))
);


--
-- Name: COLUMN jobs.genre; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.jobs.genre IS 'User selected gender: Homme or Femme';


--
-- Name: COLUMN jobs.angle; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.jobs.angle IS 'User selected angle: face, Profil, dos, Trois-quarts face';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    discord_id character varying(20) NOT NULL,
    discord_name character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    last_seen_at timestamp without time zone DEFAULT now(),
    total_jobs integer DEFAULT 0,
    is_active boolean DEFAULT true
);


--
-- Name: job_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_logs ALTER COLUMN id SET DEFAULT nextval('public.job_logs_id_seq'::regclass);


--
-- Name: job_logs job_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_logs
    ADD CONSTRAINT job_logs_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: users users_discord_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_discord_id_key UNIQUE (discord_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_job_logs_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_logs_job_id ON public.job_logs USING btree (job_id);


--
-- Name: idx_jobs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_created_at ON public.jobs USING btree (created_at);


--
-- Name: idx_jobs_garment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_garment ON public.jobs USING btree (garment);


--
-- Name: idx_jobs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_status ON public.jobs USING btree (status);


--
-- Name: idx_jobs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_user_id ON public.jobs USING btree (user_id);


--
-- Name: idx_users_discord_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_discord_id ON public.users USING btree (discord_id);


--
-- Name: jobs trg_n8n_new_job; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_n8n_new_job AFTER INSERT ON public.jobs FOR EACH ROW EXECUTE FUNCTION public.notify_n8n_new_job();


--
-- Name: job_logs job_logs_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_logs
    ADD CONSTRAINT job_logs_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE;


--
-- Name: jobs jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict DrKZdoxQ4LxPrVWcOTmRMr3zb0pae2aIvBaDF1I5kYJ27whkiUYPtKutM72fk8U

