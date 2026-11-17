-- 团队随机试验：名册、发放台账与结案
-- 对应 ORM 首次建表（src/models/entities.py），与 001_initial.sql 并列保留 DDL。

CREATE TABLE public.experiments (
    id integer NOT NULL,
    name character varying(100),
    seed integer,
    treated_count integer,
    state character varying(20),
    assigned_at character varying(40),
    created character varying(40)
);

CREATE SEQUENCE public.experiments_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.experiments_id_seq OWNED BY public.experiments.id;
ALTER TABLE ONLY public.experiments ALTER COLUMN id SET DEFAULT nextval('public.experiments_id_seq'::regclass);
ALTER TABLE ONLY public.experiments ADD CONSTRAINT experiments_pkey PRIMARY KEY (id);

CREATE TABLE public.experiment_teams (
    id integer NOT NULL,
    experiment_id integer,
    name character varying(40),
    assigned_group character varying(10)
);

CREATE SEQUENCE public.experiment_teams_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.experiment_teams_id_seq OWNED BY public.experiment_teams.id;
ALTER TABLE ONLY public.experiment_teams ALTER COLUMN id SET DEFAULT nextval('public.experiment_teams_id_seq'::regclass);
ALTER TABLE ONLY public.experiment_teams ADD CONSTRAINT experiment_teams_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.experiment_teams ADD CONSTRAINT experiment_teams_experiment_id_name_key UNIQUE (experiment_id, name);
ALTER TABLE ONLY public.experiment_teams
    ADD CONSTRAINT experiment_teams_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);

CREATE TABLE public.experiment_advisors (
    id integer NOT NULL,
    experiment_id integer,
    team_id integer,
    code character varying(60)
);

CREATE SEQUENCE public.experiment_advisors_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.experiment_advisors_id_seq OWNED BY public.experiment_advisors.id;
ALTER TABLE ONLY public.experiment_advisors ALTER COLUMN id SET DEFAULT nextval('public.experiment_advisors_id_seq'::regclass);
ALTER TABLE ONLY public.experiment_advisors ADD CONSTRAINT experiment_advisors_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.experiment_advisors ADD CONSTRAINT experiment_advisors_experiment_id_code_key UNIQUE (experiment_id, code);
ALTER TABLE ONLY public.experiment_advisors
    ADD CONSTRAINT experiment_advisors_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);
ALTER TABLE ONLY public.experiment_advisors
    ADD CONSTRAINT experiment_advisors_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.experiment_teams(id);

CREATE TABLE public.ledger_entries (
    id integer NOT NULL,
    experiment_id integer,
    advisor_id integer,
    assigned_script character varying(10),
    executed_script character varying(10),
    before double precision,
    after double precision,
    late boolean,
    updated character varying(40)
);

CREATE SEQUENCE public.ledger_entries_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.ledger_entries_id_seq OWNED BY public.ledger_entries.id;
ALTER TABLE ONLY public.ledger_entries ALTER COLUMN id SET DEFAULT nextval('public.ledger_entries_id_seq'::regclass);
ALTER TABLE ONLY public.ledger_entries ADD CONSTRAINT ledger_entries_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.ledger_entries ADD CONSTRAINT ledger_entries_advisor_id_key UNIQUE (advisor_id);
ALTER TABLE ONLY public.ledger_entries
    ADD CONSTRAINT ledger_entries_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);
ALTER TABLE ONLY public.ledger_entries
    ADD CONSTRAINT ledger_entries_advisor_id_fkey FOREIGN KEY (advisor_id) REFERENCES public.experiment_advisors(id);

CREATE TABLE public.closings (
    id integer NOT NULL,
    experiment_id integer,
    attempt integer,
    state character varying(20),
    snapshot json,
    result json,
    error text,
    created character varying(40),
    finished character varying(40)
);

CREATE SEQUENCE public.closings_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.closings_id_seq OWNED BY public.closings.id;
ALTER TABLE ONLY public.closings ALTER COLUMN id SET DEFAULT nextval('public.closings_id_seq'::regclass);
ALTER TABLE ONLY public.closings ADD CONSTRAINT closings_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.closings
    ADD CONSTRAINT closings_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id);
