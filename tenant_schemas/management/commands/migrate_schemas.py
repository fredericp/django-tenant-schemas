import django
from optparse import NO_DEFAULT

if django.VERSION >= (1, 7, 0):
    from django.core.management.commands.migrate import Command as MigrateCommand
    from django.db.migrations.recorder import MigrationRecorder
from django.db import connection
from django.conf import settings

from tenant_schemas.utils import get_tenant_model, get_public_schema_name, schema_exists
from tenant_schemas.management.commands import SyncCommon


class MigrateSchemasCommand(SyncCommon):
    help = "Updates database schema. Manages both apps with migrations and those without."

    def add_arguments(self, parser):
        super(MigrateSchemasCommand, self).add_arguments(parser)
        m = MigrateCommand()
        m.add_arguments(parser)

    def handle(self, *args, **options):
        super(MigrateSchemasCommand, self).handle(*args, **options)
        self.PUBLIC_SCHEMA_NAME = get_public_schema_name()

        if self.sync_public and not self.schema_name:
            self.schema_name = self.PUBLIC_SCHEMA_NAME

        if self.sync_public:
            self.run_migrations(self.schema_name, settings.SHARED_APPS, options)
        if self.sync_tenant:
            if self.schema_name and self.schema_name != self.PUBLIC_SCHEMA_NAME:
                if not schema_exists(self.schema_name):
                    raise RuntimeError('Schema "{}" does not exist'.format(
                        self.schema_name))
                else:
                    self.run_migrations(self.schema_name, settings.TENANT_APPS, options)
            else:
                all_tenants = get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
                for tenant in all_tenants:
                    self.run_migrations(tenant.schema_name, settings.TENANT_APPS, options)

    def run_migrations(self, schema_name, included_apps, options):
        self._notice("=== Running migrate for schema %s" % schema_name)
        connection.set_schema(schema_name)
        command = MigrateCommand()
        command.execute(*self.args, **options)
        connection.set_schema_to_public()

    def _notice(self, output):
        self.stdout.write(self.style.NOTICE(output))


if django.VERSION >= (1, 7, 0):
    Command = MigrateSchemasCommand
else:
    from .legacy.migrate_schemas import Command
