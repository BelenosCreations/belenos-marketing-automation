"""CI tests for selected but explicitly unprovisioned BAM hosting plan."""
import copy
import unittest
from pathlib import Path
from hosting_plan_contract import (
    load_planned_hosting,verify_planning_only_contract)

ROOT=Path(__file__).resolve().parent


class HostingPlanContractTests(unittest.TestCase):
    def setUp(self):
        self.plan=load_planned_hosting()

    def test_owner_selected_baseline_is_explicitly_not_activated(self):
        report=verify_planning_only_contract(self.plan)
        self.assertEqual(report['status'],'planning_only')
        self.assertEqual(report['estimated_base_usd_month'],7)
        self.assertEqual(report['additional_costs_approved_usd_month'],0)
        self.assertEqual(report['development_budget_additional_usd_month'],0)
        self.assertEqual(report['deferred_render_starter_estimate_usd_month'],7)
        self.assertFalse(report['free_render_provisioning_allowed'])
        self.assertFalse(report['free_neon_provisioning_allowed'])
        self.assertFalse(report['edgepilot_host_sharing_allowed'])
        self.assertTrue(report[
            'explicit_owner_approval_required_for_budget_change'])
        self.assertFalse(report['provisioning_allowed'])
        self.assertFalse(report['live_social_publishing_allowed'])
        self.assertFalse(report['paid_ai_allowed'])
        self.assertFalse(report['plan_is_automatic_spending_cap'])
        self.assertEqual(self.plan['web_service']['render_service_id'],None)
        self.assertEqual(self.plan['database']['neon_project_id'],None)

    def test_no_render_blueprint_automatically_provisions_any_resource(self):
        self.assertFalse((ROOT/'render.yaml').exists())
        self.assertFalse((ROOT/'render.yml').exists())

    def test_changes_to_hosting_prices_tiers_and_separation_fail(self):
        changes=(
            ('web_service','estimated_usd_month',0),
            ('web_service','estimated_usd_month',10),
            ('web_service','instance_type','free'),
            ('web_service','type','reuse_edgepilot'),
            ('web_service','instance_count',2),
            ('web_service','workspace_plan_for_estimate','pro'),
            ('web_service','render_service_id','srv-real'),
            ('database','plan','launch'),
            ('database','type','share_trading_db'),
            ('database','neon_project_id','db-real'),
            ('cost_and_approval','other_monthly_spend_authorized_usd',1),
            ('cost_and_approval','service_creation_authorized',True),
            ('development_policy','monthly_new_spend_authorized_usd',1),
            ('development_policy','monthly_new_spend_authorized_usd',True),
            ('development_policy','mode','pay_as_you_go'),
            ('development_policy','render_starter_plan_deferred',False),
            ('development_policy','render_free_provisioning_authorized',True),
            ('development_policy','neon_free_provisioning_authorized',True),
            ('development_policy','share_existing_edgepilot_host_authorized',True),
            ('development_policy','paid_or_overage_services_authorized',True),
            ('development_policy','explicit_owner_approval_required_for_any_new_spend',False),
            ('development_policy','budget_review_when','automatically_after_beta'),
            ('cost_and_approval','credit_card_charges_authorized',True),
            ('cost_and_approval','free_tier_overages_guaranteed_capped',True),
            ('deployment','application_created',True),
            ('deployment','database_created',True),
            ('deployment','domain_or_subdomain','bam.example.com'),
            ('deployment','auto_deploy_allowed',True),
            ('deployment','production_database_migration_complete',True),
            ('activation','public_access',True),
            ('activation','paid_ai_calls',True),
            ('activation','social_publishing',True),
            ('activation','real_email_delivery',True),
            ('activation','scheduled_job_execution',True),
        )
        for group,key,val in changes:
            with self.subTest(group=group,key=key):
                candidate=copy.deepcopy(self.plan)
                candidate[group][key]=val
                with self.assertRaises(ValueError):
                    verify_planning_only_contract(candidate)

    def test_extra_fields_or_malformed_values_fail_closed(self):
        for change in ('unknown_root','unknown_activation',
                       'unknown_development_policy','bad_type'):
            with self.subTest(change=change):
                bad=copy.deepcopy(self.plan)
                if change=='unknown_root':
                    bad['database_connection_url']='postgresql://secret'
                elif change=='unknown_activation':
                    bad['activation']['live_billing']=False
                elif change=='unknown_development_policy':
                    bad['development_policy']['silent_monthly_budget']=10
                else:
                    bad['web_service']['estimated_usd_month']=True
                with self.assertRaises(ValueError):
                    verify_planning_only_contract(bad)


if __name__=='__main__':
    unittest.main()
