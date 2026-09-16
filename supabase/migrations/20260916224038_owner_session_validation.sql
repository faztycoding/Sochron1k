SET local check_function_bodies = off;

CREATE SCHEMA "sochron_private";

CREATE OR REPLACE FUNCTION public.sochron_session_active (
  p_session_id uuid
)
  RETURNS boolean
  LANGUAGE sql
  STABLE
  SET search_path TO ''
  AS $function$
  select sochron_private.session_active(p_session_id);
$function$;

CREATE OR REPLACE FUNCTION sochron_private.session_active (
  p_session_id uuid
)
  RETURNS boolean
  LANGUAGE sql
  STABLE
  SECURITY DEFINER
  SET search_path TO ''
  AS $function$
  select exists (
    select 1 from auth.sessions as session
    where session.id = p_session_id
      and session.user_id = (select auth.uid())
      and (session.not_after is null or session.not_after > now())
  );
$function$;

REVOKE ALL ON FUNCTION "public"."sochron_session_active"(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "public"."sochron_session_active"(uuid) TO "authenticated", "postgres";

REVOKE ALL ON FUNCTION "sochron_private"."session_active"(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "sochron_private"."session_active"(uuid) TO "authenticated", "postgres";

GRANT USAGE ON SCHEMA "sochron_private" TO "authenticated";

GRANT CREATE, USAGE ON SCHEMA "sochron_private" TO "postgres";
