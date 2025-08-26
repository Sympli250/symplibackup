<?php include 'includes/header.php'; ?>

<main class="devices-section">
  <h2 class="text-2xl mb-6">
    Tableau de bord Symplibackup
    <span style="font-size:0.7em;color:var(--fluent-subtle-text);margin-left:1em;">v0.9.7 - 2025-07-03</span>
  </h2>

  <div class="super-tabs" id="super-tabs">
    <input type="radio" id="tab-clients" name="main-tabs" checked>
    <label for="tab-clients" class="super-tab" tabindex="0"><span class="tab-label">Clients</span></label>
    <div class="super-tab-indicator"></div>
  </div>

  <div class="device-table-container tabcontent" id="tabcontent-clients">
    <div class="table-title-row">
      Liste des clients
    </div>
    <div class="table-responsive">
      <table class="devices-table" id="clients-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nom</th>
            <th style="text-align:center;">Taille utilisée</th>
            <th style="text-align:center;">Actions</th>
            <th style="text-align:center;">Lien installeur</th>
          </tr>
        </thead>
        <tbody>
        <?php
        $api_url = "http://storage.symplissime.fr:55417";
        function api_get($endpoint) {
            global $api_url;
            $url = rtrim($api_url, '/') . $endpoint;
            $ctx = stream_context_create(['http' => ['timeout' => 10]]);
            $json = @file_get_contents($url, false, $ctx);
            return $json === false ? null : json_decode($json, true);
        }
        // Récupère la liste des clients (avec colonne download_url)
        $clients = api_get('/clients');
        if (empty($clients) || !is_array($clients)): ?>
          <tr><td colspan="5">Aucun client trouvé.</td></tr>
        <?php else:
          foreach ($clients as $c):
            $client_id = $c['id'];
            $client_name = $c['name'];
            $used_data = api_get('/client/' . $client_id . '/used_space');
            $size_mo = ($used_data && isset($used_data['used_bytes'])) ? number_format($used_data['used_bytes']/1048576,2,',',' ') . ' Mo' : "-";
            $installer_url = isset($c['installer_download_url']) && $c['installer_download_url']
              ? rtrim($api_url, "/") . $c['installer_download_url']
              : null;
        ?>
          <tr class="client-row" tabindex="0" data-client-id="<?= htmlspecialchars($client_id) ?>" data-client-name="<?= htmlspecialchars($client_name) ?>">
            <td><?= htmlspecialchars($client_id) ?></td>
            <td><?= htmlspecialchars($client_name) ?></td>
            <td style="text-align:center;">
              <span class="used-size"><?= $size_mo ?></span>
            </td>
            <td style="text-align:center;">
              <form method="post" action="<?= htmlspecialchars($api_url) ?>/generate_installer"
                    class="installer-form"
                    data-client-id="<?= htmlspecialchars($client_id); ?>"
                    data-client-name="<?= htmlspecialchars($client_name); ?>">
                <input type="hidden" name="client_name" value="<?= htmlspecialchars($client_name); ?>">
                <input type="hidden" name="group" value="<?= htmlspecialchars($c['group'] ?? ''); ?>">
                <button type="submit" class="btn btn-primary">Générer l'installeur</button>
                <div class="debug-install text-red-700 text-sm mt-1"></div> <!-- Styled for error messages -->
              </form>
            </td>
            <td style="text-align:center;" id="installer-link-<?= $client_id ?>">
              <?php if ($installer_url): ?>
                <a href="<?= htmlspecialchars($installer_url) ?>" class="btn btn-success" target="_blank">Télécharger</a>
              <?php else: ?>
                <span class="text-gray-500">Non généré</span>
              <?php endif; ?>
            </td>
          </tr>
        <?php endforeach; endif ?>
        </tbody>
      </table>
    </div>
  </div>

  <div id="client-backups-modal" class="modal">
    <div class="modal-content">
      <span class="close-modal" id="close-modal" tabindex="0">&times;</span>
      <h3>Sauvegardes du client <span id="modal-client-name"></span></h3>
      <div id="modal-backups-content" class="max-h-60vh overflow-auto"></div>
    </div>
  </div>
</main>

<script>
document.addEventListener('DOMContentLoaded', function() {
  // Tabs JavaScript (similar to compte.php)
  const tabsContainer = document.getElementById('super-tabs');
  const tabInputs = tabsContainer.querySelectorAll('input[name="main-tabs"]');
  const tabContents = document.querySelectorAll('.tabcontent'); // Assuming tabcontent class for dashboard tabs
  const indicator = tabsContainer.querySelector('.super-tab-indicator');

  function updateTabDisplay() {
    tabContents.forEach(content => {
      content.style.display = 'none';
    });

    const checkedInput = tabsContainer.querySelector('input[name="main-tabs"]:checked');
    if (checkedInput) {
      const targetId = checkedInput.id.replace('tab-', 'tabcontent-');
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.style.display = '';
      }
    }
  }

  function updateIndicatorPosition() {
    const checkedTabLabel = tabsContainer.querySelector('input[name="main-tabs"]:checked + .super-tab');
    if (checkedTabLabel && indicator) {
      indicator.style.left = checkedTabLabel.offsetLeft + 'px';
      indicator.style.width = checkedTabLabel.offsetWidth + 'px';
    }
  }

  tabInputs.forEach(input => {
    input.addEventListener('change', () => {
      updateTabDisplay();
      updateIndicatorPosition();
    });
  });

  // Initial calls on load
  updateTabDisplay();
  updateIndicatorPosition();

  // Update indicator on window resize
  window.addEventListener('resize', updateIndicatorPosition);


  // MODAL pour sauvegardes client
  const modal = document.getElementById('client-backups-modal');
  const closeModalBtn = document.getElementById('close-modal');
  let lastSelected = null;

  function showBackupsModal(clientId, clientName) {
    if(lastSelected) lastSelected.classList.remove('selected');
    const row = document.querySelector('tr[data-client-id="'+clientId+'"]');
    if(row) row.classList.add('selected');
    lastSelected = row;
    document.getElementById('modal-client-name').textContent = clientName + ' (ID ' + clientId + ')';
    document.getElementById('modal-backups-content').innerHTML = '<em>Chargement...</em>';
    fetch('http://storage.symplissime.fr:55417/backups/' + clientId)
      .then(resp => resp.json())
      .then(data => {
        if(data.error) {
          document.getElementById('modal-backups-content').innerHTML = '<span class="text-red-700">'+data.error+'</span>';
          return;
        }
        let html = '';
        html += '<h4 class="text-lg font-semibold mt-4 mb-2">Backups fichiers</h4>';
        if(!data.file_backups || !data.file_backups.length) {
          html += '<div class="text-gray-600 mb-4">Aucune sauvegarde fichier trouvée.</div>';
        } else {
          html += '<table class="devices-table"><thead><tr><th>ID</th><th>Date</th><th>Taille</th><th>Type</th><th>Incremental</th></tr></thead><tbody>';
          data.file_backups.forEach(function(b){
            html += '<tr>'+
              '<td>'+b.id+'</td>'+
              '<td>'+(b.backup_time ? new Date(b.backup_time*1000).toLocaleString() : '')+'</td>'+
              '<td>'+(b.size_bytes ? (b.size_bytes/1048576).toFixed(2)+' Mo' : '-')+'</td>'+
              '<td>Fichiers</td>'+
              '<td>'+(b.incremental ? 'Oui' : 'Non')+'</td>'+
              '</tr>';
          });
          html += '</tbody></table>';
        }
        html += '<h4 class="text-lg font-semibold mt-4 mb-2">Backups images</h4>';
        if(!data.image_backups || !data.image_backups.length) {
          html += '<div class="text-gray-600">Aucune sauvegarde image trouvée.</div>';
        } else {
          html += '<table class="devices-table"><thead><tr><th>ID</th><th>Date</th><th>Taille</th><th>Lettre</th><th>Incremental</th></tr></thead><tbody>';
          data.image_backups.forEach(function(b){
            html += '<tr>'+
              '<td>'+b.id+'</td>'+
              '<td>'+(b.backup_time ? new Date(b.backup_time*1000).toLocaleString() : '')+'</td>'+
              '<td>'+(b.size_bytes ? (b.size_bytes/1048576).toFixed(2)+' Mo' : '-')+'</td>'+
              '<td>'+(b.letter || '-')+'</td>'+
              '<td>'+(b.incremental ? 'Oui' : 'Non')+'</td>'+
              '</tr>';
          });
          html += '</tbody></table>';
        }
        document.getElementById('modal-backups-content').innerHTML = html;
      })
      .catch(err => {
        document.getElementById('modal-backups-content').innerHTML = '<span class="text-red-700">Erreur de chargement des sauvegardes.</span>';
      });
    modal.style.display = "block";
  }

  document.querySelectorAll('tr.client-row').forEach(function(row){
    row.addEventListener('click', function(){
      showBackupsModal(this.dataset.clientId, this.dataset.clientName);
    });
    row.addEventListener('keydown', function(e){
      if (e.key === "Enter" || e.key === " ") {
        showBackupsModal(this.dataset.clientId, this.dataset.clientName);
      }
    });
    row.tabIndex = 0;
  });

  closeModalBtn.onclick = function() { modal.style.display='none'; if(lastSelected) lastSelected.classList.remove('selected'); }
  closeModalBtn.onkeydown = function(e){ if(e.key==="Enter"||e.key===" "){ closeModalBtn.click(); } }
  window.onclick = function(event) { if(event.target === modal) { modal.style.display = "none"; if(lastSelected) lastSelected.classList.remove('selected'); } }

  // ----------- INSTALLER GENERATION FORM -----------
  document.querySelectorAll('.installer-form').forEach(function(form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      const debugDiv = form.querySelector('.debug-install');
      debugDiv.style.color = "var(--fluent-subtle-text)"; // Use a neutral color for info
      debugDiv.textContent = "Envoi de la requête…";
      const btn = form.querySelector('button[type=submit]');
      btn.disabled = true;
      const clientId = form.dataset.clientId;

      const formData = new FormData(form);

      fetch(form.action, {
        method: "POST",
        body: formData,
        credentials: "omit"
      }).then(async resp => {
        let data = null;
        try { data = await resp.json(); } catch {}
        if (resp.ok && data && data.download_url) {
          debugDiv.style.color = "var(--fluent-primary)"; // Green for success
          debugDiv.innerHTML = "Succès : installeur généré.";
          const linkTd = document.getElementById('installer-link-' + clientId);
          if (linkTd) {
            linkTd.innerHTML =
              '<a href="'+data.download_url+'" class="btn btn-success" target="_blank">Télécharger</a>';
          }
        } else if (!resp.ok) {
          debugDiv.style.color = "#b70000"; // Red for error
          let msg = `Erreur serveur (${resp.status})`;
          if (data && data.detail)
            msg += `<br><b>Détail :</b> ${data.detail}`;
          debugDiv.innerHTML = msg;
        } else {
          debugDiv.style.color = "#b70000";
          debugDiv.innerHTML = "Erreur inattendue lors de la génération.";
        }
      }).catch(err => {
        debugDiv.style.color = "#b70000";
        debugDiv.innerHTML = `<b>Erreur JS/AJAX :</b> ${err}`;
      }).finally(() => {
        btn.disabled = false;
      });
    });
  });
});
</script>
<?php include 'includes/footer.php'; ?>
