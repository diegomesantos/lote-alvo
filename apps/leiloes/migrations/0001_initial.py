# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ImovelCaixa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imovel_id_caixa', models.CharField(max_length=50, unique=True)),
                ('endereco', models.CharField(max_length=255)),
                ('cidade', models.CharField(db_index=True, max_length=100)),
                ('estado', models.CharField(db_index=True, max_length=2)),
                ('cep', models.CharField(blank=True, max_length=10, null=True)),
                ('tipo', models.CharField(choices=[('apto', 'Apartamento'), ('casa', 'Casa'), ('sala', 'Sala Comercial'), ('lote', 'Lote'), ('galpao', 'Galpão')], db_index=True, max_length=20)),
                ('quartos', models.IntegerField(blank=True, null=True)),
                ('area_util', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('valor_avaliacao', models.DecimalField(decimal_places=2, max_digits=12)),
                ('percentual_desconto', models.DecimalField(decimal_places=2, max_digits=5)),
                ('valor_minimo_lance', models.DecimalField(decimal_places=2, max_digits=12)),
                ('valor_final', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('data_leilao', models.DateField(db_index=True)),
                ('hora_leilao', models.TimeField(blank=True, null=True)),
                ('tipo_leilao', models.CharField(choices=[('extra', 'Extrajudicial'), ('judicial', 'Judicial')], max_length=20)),
                ('formas_pagamento', models.JSONField(default=dict)),
                ('edital_url', models.URLField(blank=True, null=True)),
                ('matricula_url', models.URLField(blank=True, null=True)),
                ('foto_url', models.URLField(blank=True, null=True)),
                ('ocupado', models.BooleanField(default=True)),
                ('pendencias', models.JSONField(default=list)),
                ('possui_penhora', models.BooleanField(default=False)),
                ('sincronizado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Imóvel Caixa',
                'verbose_name_plural': 'Imóveis Caixa',
                'ordering': ['-data_leilao', '-valor_avaliacao'],
            },
        ),
    ]
