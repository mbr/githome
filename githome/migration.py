import logbook

# contains the version number of the first occurence of a specific database
# revision
DB_REVISIONS = ['0.2', '0.3']

log = logbook.Logger('migration')


_upgrades = {}


def upgrades_to(version):
    def decorator(f):
        _upgrades[version] = f
        return f
    return decorator


def get_upgrade_path(gh):
    return [_upgrades[i+1]
            for i in range(gh.get_db_revision(), len(_upgrades))]


@upgrades_to(1)
def v1(con):
    log.info('Upgrading to database revision 1')
