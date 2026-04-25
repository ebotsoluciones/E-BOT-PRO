{% extends "base.html" %}
{% block title %}Reportes{% endblock %}
{% block page_title %}Reportes{% endblock %}

{% block content %}

<!-- Filtros -->
<div class="card" style="margin-bottom:20px;">
  <form method="GET" style="display:flex; gap:12px; align-items:flex-end; flex-wrap:wrap;">
    <div class="form-group" style="margin:0; flex:1; min-width:180px;">
      <label>Profesional</label>
      <select name="prof_id">
        <option value="">Consolidado clínica</option>
        {% for p in profs %}
          <option value="{{ p.id }}" {% if p.id == prof_id %}selected{% endif %}>
            {{ p.last_name }}, {{ p.first_name }}{% if p.specialty %} — {{ p.specialty }}{% endif %}
          </option>
        {% endfor %}
      </select>
    </div>
    <div class="form-group" style="margin:0; min-width:130px;">
      <label>Desde</label>
      <input type="date" name="desde" value="{{ desde }}">
    </div>
    <div class="form-group" style="margin:0; min-width:130px;">
      <label>Hasta</label>
      <input type="date" name="hasta" value="{{ hasta }}">
    </div>
    <button type="submit" class="btn btn-primary">Ver reporte</button>
    <button type="submit" name="modo" value="todo" class="btn">Todo el historial</button>
  </form>
</div>

<!-- Resumen -->
<div class="stat-grid" style="margin-bottom:24px;">
  <div class="stat-card">
    <div class="label">Turnos en el período</div>
    <div class="value">{{ reporte.summary.total or 0 }}</div>
  </div>
  <div class="stat-card">
    <div class="label">Pacientes únicos</div>
    <div class="value">{{ reporte.summary.unique_patients or 0 }}</div>
  </div>
</div>

<!-- Detalle -->
<div class="card" style="margin-bottom:20px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
    <div class="card-title" style="margin:0;">Detalle de turnos</div>
    {% if reporte.detail %}
    <button class="btn btn-sm" onclick="document.getElementById('panel-borrar').style.display='block'">
      🗑 Borrar histórico
    </button>
    {% endif %}
  </div>

  <!-- Panel borrar histórico -->
  <div id="panel-borrar" style="display:none; background:#fcebeb; border:1px solid #f09595;
       border-radius:6px; padding:12px; margin-bottom:16px;">
    <div style="font-size:13px; font-weight:500; color:#791f1f; margin-bottom:8px;">
      ⚠️ Borrar turnos anteriores a una fecha
    </div>
    <div style="font-size:12px; color:#791f1f; margin-bottom:10px;">
      Esta acción elimina permanentemente los turnos. El historial de pacientes se mantiene.
    </div>
    <form method="POST" action="{{ url_for('web.borrar_historico') }}"
          onsubmit="return confirm('¿Confirmar borrado de turnos anteriores a esa fecha?')">
      <div style="display:flex; gap:8px; align-items:flex-end;">
        <div class="form-group" style="margin:0;">
          <label style="color:#791f1f;">Borrar anteriores a:</label>
          <input type="date" name="hasta_fecha" required>
        </div>
        {% if prof_id %}<input type="hidden" name="prof_id" value="{{ prof_id }}">{% endif %}
        <button type="submit" class="btn btn-danger">Confirmar borrado</button>
        <button type="button" class="btn"
          onclick="document.getElementById('panel-borrar').style.display='none'">
          Cancelar
        </button>
      </div>
    </form>
  </div>

  {% if reporte.detail %}
    <table>
      <thead>
        <tr>
          <th>Fecha</th>
          <th>Hora</th>
          <th>Paciente</th>
          <th>Obra social</th>
          {% if not prof_id %}<th>Profesional</th>{% endif %}
        </tr>
      </thead>
      <tbody>
        {% for t in reporte.detail %}
        <tr>
          <td style="white-space:nowrap;">{{ t.date.strftime('%d/%m/%Y') }}</td>
          <td>{{ t.time.strftime('%H:%M') }}</td>
          <td>{{ t.patient_name }}</td>
          <td style="color:#6b6a64;">{{ t.obra_social or '—' }}</td>
          {% if not prof_id %}
            <td style="color:#6b6a64;">{{ t.prof_last_name }}, {{ t.prof_first_name }}</td>
          {% endif %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <div style="font-size:12px; color:#6b6a64; margin-top:10px;">
      Mostrando del {{ desde }} al {{ hasta }}
    </div>
  {% else %}
    <div class="empty">Sin turnos para el período seleccionado.</div>
  {% endif %}
</div>

{% endblock %}
