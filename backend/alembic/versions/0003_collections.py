from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None
def upgrade():
    columns={c['name'] for c in sa.inspect(op.get_bind()).get_columns('papers')}
    if 'collection_kind' not in columns: op.add_column('papers',sa.Column('collection_kind',sa.String(),nullable=False,server_default='full'))
    if 'expected_count' not in columns: op.add_column('papers',sa.Column('expected_count',sa.Integer(),nullable=True))
def downgrade(): raise RuntimeError('请先备份，不自动移除用户题集设置')
