revision = '4160ccb58402'
down_revision = None
branch_labels = None
depends_on = None

import json
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


sections = {
    'update_authorized_keys': 'local',
    'authorized_keys_file': 'local',
    'githome_executable': 'local',
    'githome_id': 'githome',
}


def upgrade():
    con = op.get_bind()

    old_cfg = table('configsetting',
                    column('key', sa.String),
                    column('json_value', sa.String))

    # check we know where to put each key
    for key, value in con.execute(old_cfg.select()):
        if key not in sections:
            raise RuntimeError('Cannot migrate configuration, unknown '
                               'configuration value: {}'.format(key))

    new_cfg = op.create_table('config',
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('section', sa.String(), nullable=False),
    sa.Column('data', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('key', 'section')
    )

    section = sections[key]
    new_recs = [{
            'key': key,
            'section': sections[key],
            'data': value,
        } for key, value in con.execute(old_cfg.select())]
    op.bulk_insert(new_cfg, new_recs)

    import githome
    gh_client = os.path.join(os.path.dirname(githome.__file__), 'gh_client')

    op.bulk_insert(new_cfg, [
        {'section': 'local', 'key': 'authorized_keys_start_marker',
         'data': r'"# -- added by githome {}, do not remove these markers --\n"'},
        {'section': 'local', 'key': 'authorized_keys_end_marker',
         'data': r'"# -- end githome {}. keep trailing newline! --\n"'},
        {'section': 'local',  'key': 'use_gh_client',
         'data': json.dumps(True)},
        {'section': 'local', 'key': 'gh_client_executable',
         'data': json.dumps(gh_client)},
    ])

    # rename config key githome_id to id
    op.execute(new_cfg.update().where(new_cfg.c['key'] == 'githome_id')
                               .values(key='id'))

    op.rename_table('user', 'users')
    op.rename_table('public_key', 'public_keys')
    op.drop_table('configsetting')
