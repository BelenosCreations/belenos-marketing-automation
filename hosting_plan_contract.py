"""Offline CI guard for BAM's owner-selected *unprovisioned* hosting design.

This module validates the tracked planning artifact only. It cannot create,
stop or govern an actual Render/Neon account. True operational cost ceilings
must be set and audited separately with those providers before deployment.
"""
import json
from pathlib import Path


def load_planned_hosting(path=None):
    file=Path(path) if path is not None else Path(__file__).with_name(
        'BAM_HOSTING_PLAN.json')
    return json.loads(file.read_text(encoding='utf-8'))


def verify_planning_only_contract(plan):
    """Fail on drift that would silently turn a design into approval.

    Intentional owner-approved deployment requires separately reviewed
    changes to the release process and these guardrails, not a client toggle.
    """
    if type(plan) is not dict or set(plan)!={
            'schema_version','decision_date','status','project',
            'web_service','database','cost_and_approval','activation',
            'deployment'}:
        raise ValueError('Invalid BAM hosting plan schema')
    if (plan['schema_version']!=1 or
            plan['decision_date']!='2026-11-12' or
            plan['status']!='planning_only' or
            plan['project']!='Belenos Automatic Marketing'):
        raise ValueError('BAM hosting is planning-only')
    web=plan['web_service']
    if type(web) is not dict or web!={
            'provider':'render','instance_type':'starter',
            'type':'new_dedicated_web_service',
            'workspace_plan_for_estimate':'hobby','instance_count':1,
            'estimated_usd_month':7,'memory_mb':512,
            'render_service_id':None}:
        raise ValueError('Expected one uncreated $7 Render Starter web service')
    db=plan['database']
    if type(db) is not dict or db!={
            'provider':'neon','plan':'free',
            'type':'new_separate_postgresql_project',
            'estimated_usd_month':0,'storage_gb_per_project':1,
            'cu_hours_per_project_month':100,'neon_project_id':None}:
        raise ValueError('Expected one uncreated free Neon PostgreSQL project')
    cost=plan['cost_and_approval']
    if type(cost) is not dict or cost!={
            'estimated_base_usd_month':7,
            'other_monthly_spend_authorized_usd':0,
            'service_creation_authorized':False,
            'credit_card_charges_authorized':False,
            'free_tier_overages_guaranteed_capped':False}:
        raise ValueError('Cost approval exceeds selected planning-only scope')
    activation=plan['activation']
    expected_activation={
        'public_access','live_user_enrollment','google_oauth_real',
        'meta_oauth_real','social_publishing','scheduled_job_execution',
        'paid_ai_calls','real_email_delivery','billable_media_storage'}
    if (type(activation) is not dict or set(activation)!=expected_activation
            or any(type(value) is not bool or value
                   for value in activation.values())):
        raise ValueError('Live/paid services must remain disabled')
    deploy=plan['deployment']
    expected_deploy={
        'application_created','database_created','release_entrypoint_approved',
        'production_database_migration_complete',
        'encrypted_backup_restore_verified',
        'multi_tenant_live_tests_verified','domain_or_subdomain',
        'auto_deploy_allowed'}
    if (type(deploy) is not dict or set(deploy)!=expected_deploy
            or deploy['domain_or_subdomain'] is not None
            or any(type(v) is not bool or v
                   for k,v in deploy.items() if k!='domain_or_subdomain')):
        raise ValueError('No deployment approval or live release evidence exists')
    return {
        'status':'planning_only',
        'provisioning_allowed':False,
        'live_social_publishing_allowed':False,
        'paid_ai_allowed':False,
        'estimated_base_usd_month':7,
        'additional_costs_approved_usd_month':0,
        'plan_is_automatic_spending_cap':False,
    }
