from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leiloes', '0004_imovelcaixa_ativo_caixa_and_sync_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='imovelcaixa',
            name='despesa_condominio',
            field=models.CharField(
                choices=[
                    ('comprador', 'Por conta do comprador'),
                    ('comprador_ate_10', 'Comprador até 10% (Caixa paga o excedente)'),
                    ('caixa', 'Quitado pela Caixa'),
                    ('indeterminado', 'Não informado'),
                ],
                db_index=True,
                default='indeterminado',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='imovelcaixa',
            name='despesa_tributos',
            field=models.CharField(
                choices=[
                    ('comprador', 'Por conta do comprador'),
                    ('comprador_ate_10', 'Comprador até 10% (Caixa paga o excedente)'),
                    ('caixa', 'Quitado pela Caixa'),
                    ('indeterminado', 'Não informado'),
                ],
                db_index=True,
                default='indeterminado',
                max_length=20,
            ),
        ),
    ]
