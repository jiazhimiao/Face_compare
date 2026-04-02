const tokenInput = document.getElementById('api-token');

if (tokenInput) {
  const storedToken = localStorage.getItem('face-compare-token');
  if (storedToken && !tokenInput.value) {
    tokenInput.value = storedToken;
  }

  tokenInput.addEventListener('change', () => {
    localStorage.setItem('face-compare-token', tokenInput.value.trim());
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function badgeClass(tone) {
  if (tone === 'success' || tone === 'warning' || tone === 'danger') {
    return tone;
  }
  return 'neutral';
}

function setBanner(panel, tone, badge, title, text) {
  const banner = panel.querySelector('[data-role="result-banner"]');
  banner.className = `result-banner state-${tone}`;
  banner.innerHTML = `
    <span class="status-pill ${badgeClass(tone)}">${escapeHtml(badge)}</span>
    <div>
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(text)}</p>
    </div>
  `;
}

function resetPreview(figure, emptyText) {
  const img = figure.querySelector('img');
  const empty = figure.querySelector('.preview-empty');
  img.hidden = true;
  img.removeAttribute('src');
  empty.hidden = false;
  empty.textContent = emptyText;
}

function previewImage(figure, url, emptyText) {
  const img = figure.querySelector('img');
  const empty = figure.querySelector('.preview-empty');
  if (url) {
    img.src = `${url}?t=${Date.now()}`;
    img.hidden = false;
    empty.hidden = true;
  } else {
    resetPreview(figure, emptyText);
  }
}

function setLoading(panel, submitButton) {
  setBanner(panel, 'loading', '处理中', '正在处理请求', '已提交图片，正在等待接口返回结果。');
  panel.querySelector('[data-role="result-box"]').textContent = '处理中...';
  const jsonDetails = panel.querySelector('.json-details');
  if (jsonDetails) {
    jsonDetails.open = false;
  }
  const visual = panel.querySelector('[data-role="result-visual"]');
  const visualEmpty = panel.querySelector('[data-role="visual-empty"]');
  if (visual) {
    visual.hidden = true;
    visual.removeAttribute('src');
  }
  if (visualEmpty) {
    visualEmpty.hidden = false;
    visualEmpty.textContent = '正在生成结果图，请稍候...';
  }
  panel.querySelector('[data-role="open-result"]').hidden = true;
  resetPreview(panel.querySelector('[data-role="preview-primary"]'), '等待上传');
  const secondaryCard = panel.querySelector('[data-role="preview-secondary"]');
  if (secondaryCard) {
    resetPreview(secondaryCard, '等待上传');
  }
  submitButton.disabled = true;
}

function getOperationPayload(data) {
  if (data.face_detection) {
    return {
      type: 'detect',
      statusLabel: data.face_detection.has_face ? '检测到人脸' : '未检测到人脸',
      tone: data.face_detection.has_face ? 'success' : 'danger',
      primaryMessage: data.face_detection.message,
      primaryImage: data.image_url,
      secondaryImage: '',
      visualUrl: data.visualization_url,
    };
  }

  if (data.identity_verification) {
    return {
      type: 'verify',
      statusLabel: data.identity_verification.verified ? '核验通过' : '核验未通过',
      tone: data.identity_verification.verified ? 'success' : 'warning',
      primaryMessage: data.identity_verification.message,
      primaryImage: data.id_card_url,
      secondaryImage: data.face_image_url,
      visualUrl: data.visualization_url,
    };
  }

  if (data.blacklist_check) {
    return {
      type: 'blacklist',
      statusLabel: data.blacklist_check.matched ? '命中黑名单' : '未命中黑名单',
      tone: data.blacklist_check.matched ? 'danger' : 'success',
      primaryMessage: data.blacklist_check.message,
      primaryImage: data.image_url,
      secondaryImage: data.matched_image_url,
      visualUrl: data.visualization_url,
    };
  }

  return null;
}

function renderMedia(panel, operation) {
  const visual = panel.querySelector('[data-role="result-visual"]');
  const visualEmpty = panel.querySelector('[data-role="visual-empty"]');
  const openResult = panel.querySelector('[data-role="open-result"]');
  const secondaryCard = panel.querySelector('[data-role="preview-secondary"]');

  if (operation.visualUrl && visual) {
    visual.src = `${operation.visualUrl}?t=${Date.now()}`;
    visual.hidden = false;
    if (visualEmpty) {
      visualEmpty.hidden = true;
    }
    openResult.href = operation.visualUrl;
    openResult.hidden = false;
  } else {
    if (visual) {
      visual.hidden = true;
    }
    if (visualEmpty) {
      visualEmpty.hidden = false;
      visualEmpty.textContent = operation.primaryMessage || '暂无结果图';
    }
    openResult.hidden = true;
  }

  previewImage(panel.querySelector('[data-role="preview-primary"]'), operation.primaryImage, '暂无原图');
  if (secondaryCard) {
    if (operation.type === 'detect') {
      secondaryCard.hidden = true;
    } else {
      secondaryCard.hidden = false;
      const emptyText = operation.type === 'blacklist' ? '暂无命中参考图' : '等待上传';
      previewImage(secondaryCard, operation.secondaryImage, emptyText);
    }
  }
}

async function submitForm(form) {
  const workflowCard = form.closest('.workflow-card');
  const panel = workflowCard ? workflowCard.querySelector('[data-role="result-panel"]') : null;
  if (!panel) {
    console.error('result panel not found for form');
    return;
  }
  const submitButton = form.querySelector('.submit-button');
  const resultBox = panel.querySelector('[data-role="result-box"]');
  const endpoint = form.dataset.endpoint;
  const token = tokenInput ? tokenInput.value.trim() : '';
  const requestId = `web-5100-${Date.now()}`;

  setLoading(panel, submitButton);

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'X-API-Token': token,
        'X-Request-Id': requestId
      },
      body: new FormData(form)
    });

    const payload = await response.json();
    resultBox.textContent = JSON.stringify(payload, null, 2);

    if (!payload.success) {
      setBanner(panel, 'danger', '请求失败', '请求失败', payload.message || '接口返回失败。');
      const visualEmpty = panel.querySelector('[data-role="visual-empty"]');
      if (visualEmpty) {
        visualEmpty.hidden = false;
        visualEmpty.textContent = payload.message || '请求失败';
      }
      return;
    }

    const operation = getOperationPayload(payload.data);
    if (!operation) {
      setBanner(panel, 'danger', '解析失败', '结果解析失败', '接口成功返回，但前端未识别当前数据结构。');
      return;
    }

    setBanner(panel, operation.tone, operation.statusLabel, operation.statusLabel, operation.primaryMessage);
    renderMedia(panel, operation);
  } catch (error) {
    resultBox.textContent = String(error);
    const visualEmpty = panel.querySelector('[data-role="visual-empty"]');
    if (visualEmpty) {
      visualEmpty.hidden = false;
      visualEmpty.textContent = String(error);
    }
    setBanner(panel, 'danger', '请求异常', '请求异常', String(error));
  } finally {
    submitButton.disabled = false;
  }
}

document.querySelectorAll('.tool-form').forEach((form) => {
  form.querySelectorAll('input[type="file"]').forEach((input) => {
    input.addEventListener('change', () => {
      const fileName = input.files && input.files[0] ? input.files[0].name : '未选择文件';
      const field = input.closest('.file-field');
      if (field) {
        field.querySelectorAll('.file-name').forEach((item) => {
          item.textContent = fileName;
        });
      }
      input.title = fileName;
    });
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    submitForm(form);
  });
});

document.querySelectorAll('.workflow-card').forEach((card) => {
  const tabs = card.querySelectorAll('.tab-button');
  const panels = card.querySelectorAll('.media-panel');

  tabs.forEach((button) => {
    button.addEventListener('click', () => {
      tabs.forEach((item) => item.classList.remove('is-active'));
      panels.forEach((item) => item.classList.remove('is-active'));
      button.classList.add('is-active');
      card.querySelector(`[data-tab-panel="${button.dataset.tabTarget}"]`).classList.add('is-active');
    });
  });
});
