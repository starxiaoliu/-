"""Initial import schema."""
from alembic import op
from app.db import Paper, Question, Tag
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    for model in (Paper,Question,Tag): model.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():
    raise RuntimeError('禁止自动删除本地用户数据；请先备份并人工处理')
