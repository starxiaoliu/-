"""Independent review and tag relationships."""
from alembic import op
from app.db import Review, ReviewTag
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None
def upgrade():
    Review.__table__.create(op.get_bind(), checkfirst=True)
    ReviewTag.__table__.create(op.get_bind(), checkfirst=True)
def downgrade(): raise RuntimeError('请先备份；禁止自动删除笔记')
