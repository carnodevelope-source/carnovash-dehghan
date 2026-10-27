import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from apps.vehicles.customer_tenant_repair import apply_plan, digest, make_plan, rollback, unseal, write_plan


class Command(BaseCommand):
    help = 'Preview, explicitly approve, or conditionally roll back historical customer links.'

    def add_arguments(self, parser):
        modes = parser.add_mutually_exclusive_group()
        modes.add_argument('--dry-run', action='store_true')
        modes.add_argument('--review-plan', action='store_true')
        modes.add_argument('--apply', action='store_true')
        modes.add_argument('--rollback', type=int, metavar='RUN_ID')
        parser.add_argument('--tenant', type=int)
        parser.add_argument('--plan', help='Encrypted plan path outside the repository')
        parser.add_argument('--approve-hash')

    def handle(self, *args, **options):
        try:
            if options['rollback'] is not None:
                if options['approve_hash'] != f"rollback:{options['rollback']}":
                    raise CommandError('Rollback requires --approve-hash rollback:RUN_ID.')
                rollback(options['rollback'])
                result = {'rolled_back': options['rollback']}
            elif options['review_plan']:
                if not options['plan']:
                    raise CommandError('Review requires --plan.')
                plan = unseal(Path(options['plan']).read_text(encoding='ascii'))
                result = {'plan_hash': digest(plan), 'summary': plan['summary'],
                          'actions': [{k: a[k] for k in ('vehicle', 'old_customer', 'tenant', 'target', 'kind')} for a in plan['actions']]}
            elif options['apply']:
                if not options['plan'] or not options['approve_hash']:
                    raise CommandError('Apply requires --plan and --approve-hash.')
                plan = unseal(Path(options['plan']).read_text(encoding='ascii'))
                run, count = apply_plan(plan, options['approve_hash'])
                result = {'run_id': run, 'changed_records': count}
            else:
                plan = make_plan(options['tenant'])
                if options['plan']:
                    path = Path(options['plan']).resolve()
                    repo = Path(__file__).resolve().parents[5]
                    if path.is_relative_to(repo):
                        raise CommandError('Store encrypted plans outside the repository.')
                    write_plan(path, plan)
                result = dict(plan['summary'], plan_hash=digest(plan), changed_records=0)
            self.stdout.write(json.dumps(result, sort_keys=True))
        except CommandError:
            raise
        except Exception:
            raise CommandError('Repair failed; transaction rolled back. Check configuration and regenerate the plan.') from None
