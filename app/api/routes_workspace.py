from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["workspace"])


WORKSPACE_HTML = """<!DOCTYPE html>
<html lang=\"zh-CN\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>AgentGraphRAG 工作台</title>
    <style>
      :root {
        --bg: #f2efe8;
        --panel: rgba(255,255,255,0.84);
        --line: rgba(48, 40, 30, 0.12);
        --text: #1f2522;
        --muted: #5f6d66;
        --accent: #bb5a2c;
        --accent-2: #135f57;
        --warn: #8b4d23;
        --shadow: 0 24px 64px rgba(22, 31, 26, 0.12);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        color: var(--text);
        font-family: "IBM Plex Sans", "Noto Sans SC", sans-serif;
        background:
          radial-gradient(circle at top left, rgba(187,90,44,.18), transparent 24%),
          radial-gradient(circle at bottom right, rgba(19,95,87,.14), transparent 26%),
          linear-gradient(135deg, #f6f2ea, var(--bg));
      }
      .page { max-width: 1460px; margin: 0 auto; padding: 24px 18px 48px; }
      .hero, .panel { border: 1px solid var(--line); border-radius: 28px; background: var(--panel); box-shadow: var(--shadow); }
      .hero { padding: 28px; display: grid; gap: 18px; }
      .hero__top { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
      .eyebrow { display: inline-flex; padding: 6px 10px; border-radius: 999px; background: rgba(19,95,87,.12); color: var(--accent-2); font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
      h1 { margin: 12px 0 8px; font-size: clamp(30px, 4vw, 52px); line-height: 1.02; }
      p { margin: 0; line-height: 1.6; color: var(--muted); }
      .nav { display: flex; gap: 10px; flex-wrap: wrap; }
      .nav a, button, .button-link {
        border: 0; text-decoration: none; cursor: pointer; border-radius: 999px; padding: 12px 16px;
        font: inherit; font-weight: 700; color: white; background: linear-gradient(135deg, #cc7240, #95431f);
      }
      .button-link.alt, .nav a.alt, button.alt { background: rgba(31,37,34,.08); color: var(--text); }
      .chips { display: flex; gap: 10px; flex-wrap: wrap; }
      .chip { padding: 8px 12px; border-radius: 999px; background: rgba(31,37,34,.07); font-size: 13px; color: var(--muted); }
      .grid { display: grid; grid-template-columns: 1.05fr .95fr; gap: 18px; margin-top: 18px; }
      .stack { display: grid; gap: 18px; }
      .panel { padding: 20px; }
      .panel h2 { margin: 0 0 10px; font-size: 22px; }
      .panel__intro { margin-bottom: 14px; }
      label { display: grid; gap: 8px; margin-top: 12px; font-weight: 700; }
      input, textarea, select {
        width: 100%; border: 1px solid var(--line); border-radius: 16px; padding: 12px 14px; font: inherit;
        background: rgba(252,250,246,.9); color: var(--text);
      }
      textarea { min-height: 128px; resize: vertical; }
      .actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
      .status { margin-top: 14px; padding: 12px 14px; border-radius: 16px; background: rgba(19,95,87,.09); color: var(--accent-2); font-weight: 600; white-space: pre-wrap; }
      .status.warn { background: rgba(139,77,35,.1); color: var(--warn); }
      .list { display: grid; gap: 12px; margin-top: 14px; }
      .card { border: 1px solid var(--line); border-radius: 18px; padding: 14px; background: rgba(255,255,255,.68); }
      .card strong { display: block; margin-bottom: 6px; }
      .meta { font-size: 13px; color: var(--muted); display: flex; gap: 10px; flex-wrap: wrap; }
      .answer { white-space: pre-wrap; line-height: 1.65; color: var(--text); }
      .evidence { margin-top: 12px; display: grid; gap: 10px; }
      .evidence-item { padding: 12px; border-radius: 16px; background: rgba(19,95,87,.06); border: 1px solid rgba(19,95,87,.12); }
      .mono { font-family: "IBM Plex Mono", Consolas, monospace; }
      .two-col { display:grid; grid-template-columns: 1fr 1fr; gap: 14px; }
      .subpanel { border:1px solid var(--line); border-radius:18px; padding:14px; background: rgba(255,255,255,.62); }
      .graph-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      .tiny { font-size: 12px; color: var(--muted); }
      @media (max-width: 1100px) { .grid, .two-col, .graph-grid { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <main class=\"page\">
      <section class=\"hero\">
        <div class=\"hero__top\">
          <div>
            <span class=\"eyebrow\">Workspace</span>
            <h1>AgentGraphRAG 工作台</h1>
            <p>这里直接完成本地非结构化文件上传、知识库更新、问答、trace 查看和知识内容浏览。配置页仍独立存在，用于配置 bge-m3、Qwen2.5、Milvus、Neo4j、MySQL 等外部服务。</p>
          </div>
          <div class=\"nav\">
            <a href=\"/workspace\">工作台</a>
            <a class=\"alt\" href=\"/settings\">配置中心</a>
            <a class=\"alt\" href=\"/api/v1/prompts\" target=\"_blank\" rel=\"noreferrer\">Prompt Registry</a>
            <a class=\"alt\" href=\"/health\" target=\"_blank\" rel=\"noreferrer\">健康检查</a>
          </div>
        </div>
        <div class=\"chips\">
          <span class=\"chip\">上传 -> 入库 -> 问答</span>
          <span class=\"chip\">支持 PDF / DOCX / 图片</span>
          <span class=\"chip\">展示 chunk / trace / graph snapshot</span>
        </div>
      </section>

      <div class=\"grid\">
        <section class=\"stack\">
          <section class=\"panel\">
            <h2>1. 上传并更新知识库</h2>
            <p class=\"panel__intro\">上传本地非结构化文件后，前端会自动调用上传接口和入库接口。入库完成后可直接查看文档详情和 chunk 预览。</p>
            <label>
              选择本地文件
              <input id=\"fileInput\" type=\"file\" accept=\".pdf,.doc,.docx,.png,.jpg,.jpeg,.bmp,.tif,.tiff\" />
            </label>
            <div class=\"actions\">
              <button onclick=\"uploadAndIngest()\">上传并入库</button>
              <button class=\"alt\" onclick=\"refreshWorkspace()\">刷新列表</button>
            </div>
            <div id=\"uploadStatus\" class=\"status\">等待上传。</div>
          </section>

          <section class=\"panel\">
            <h2>2. 问答</h2>
            <p class=\"panel__intro\">输入问题后调用 `/api/v1/qa/ask`。结果区会展示答案、证据、推理路径，并可进一步查看完整 trace。</p>
            <div class=\"two-col\">
              <label>
                用户 ID
                <input id=\"userId\" value=\"u001\" />
              </label>
              <label>
                会话 ID
                <input id=\"conversationId\" value=\"conv_web_001\" />
              </label>
            </div>
            <label>
              问题
              <textarea id=\"questionInput\">液压泵泄漏的可能原因有哪些？</textarea>
            </label>
            <div class=\"actions\">
              <button onclick=\"askQuestion()\">提交问答</button>
            </div>
            <div id=\"qaStatus\" class=\"status\">等待提问。</div>
          </section>

          <section class=\"panel\">
            <h2>3. 问答结果与 Trace</h2>
            <div id=\"qaResult\" class=\"list\"></div>
          </section>
        </section>

        <section class=\"stack\">
          <section class=\"panel\">
            <h2>最近文档</h2>
            <div id=\"documentsList\" class=\"list\"></div>
          </section>

          <section class=\"panel\">
            <h2>文档预览与 Chunk</h2>
            <div id=\"documentPreview\" class=\"list\"><div class=\"card\">点击左侧文档后在这里查看详情。</div></div>
          </section>

          <section class=\"panel\">
            <h2>最近入库任务</h2>
            <div id=\"jobsList\" class=\"list\"></div>
          </section>

          <section class=\"panel\">
            <h2>最近审计日志</h2>
            <div id=\"auditList\" class=\"list\"></div>
          </section>

          <section class=\"panel\">
            <h2>图谱快照</h2>
            <div id=\"graphSnapshot\" class=\"graph-grid\"></div>
          </section>
        </section>
      </div>
    </main>

    <script>
      const apiPrefix = '/api/v1';
      let latestTraceId = '';

      function escapeHtml(text) {
        return String(text || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
      }

      function setStatus(id, message, warn = false) {
        const el = document.getElementById(id);
        el.textContent = message;
        el.className = warn ? 'status warn' : 'status';
      }

      function renderCards(targetId, items, mapper) {
        const target = document.getElementById(targetId);
        if (!items.length) {
          target.innerHTML = '<div class="card">暂无数据</div>';
          return;
        }
        target.innerHTML = items.map(mapper).join('');
      }

      async function fetchJson(url, options = {}) {
        const response = await fetch(url, options);
        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || `HTTP ${response.status}`);
        }
        return response.json();
      }

      async function refreshWorkspace() {
        const [documents, jobs, logs, graph] = await Promise.all([
          fetchJson(`${apiPrefix}/documents`),
          fetchJson(`${apiPrefix}/ingestion`),
          fetchJson(`${apiPrefix}/audit/logs`),
          fetchJson(`${apiPrefix}/knowledge/graph?limit=20`),
        ]);

        renderCards('documentsList', documents.slice(0, 8), (item) => `
          <div class="card">
            <strong>${escapeHtml(item.file_name || item.document_id)}</strong>
            <div class="meta">
              <span class="mono">${escapeHtml(item.document_id)}</span>
              <span>${escapeHtml(item.doc_type || 'unknown')}</span>
              <span>${escapeHtml(item.parse_status || 'pending')}</span>
            </div>
            <div class="actions">
              <button class="alt" onclick="loadDocumentPreview('${escapeHtml(item.document_id)}')">查看详情</button>
            </div>
          </div>
        `);

        renderCards('jobsList', jobs.slice(0, 8), (item) => `
          <div class="card">
            <strong>${escapeHtml(item.job_id)}</strong>
            <div class="meta">
              <span>${escapeHtml(item.source_type)}</span>
              <span>${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.batch_id)}</span>
            </div>
            ${item.error_message ? `<div class="tiny">error: ${escapeHtml(item.error_message)}</div>` : ''}
          </div>
        `);

        renderCards('auditList', logs.slice(0, 8), (item) => `
          <div class="card">
            <strong>${escapeHtml(item.question)}</strong>
            <div class="meta">
              <span class="mono">${escapeHtml(item.trace_id)}</span>
              <span>${escapeHtml(item.route)}</span>
              <span>${escapeHtml(item.risk_level)}</span>
              <span>${escapeHtml(item.fallback_mode)}</span>
            </div>
            <div class="actions">
              <button class="alt" onclick="loadTrace('${escapeHtml(item.trace_id)}')">查看 Trace</button>
            </div>
          </div>
        `);

        renderGraph(graph);
      }

      async function loadDocumentPreview(documentId) {
        try {
          const [doc, chunks] = await Promise.all([
            fetchJson(`${apiPrefix}/documents/${documentId}`),
            fetchJson(`${apiPrefix}/documents/${documentId}/chunks?limit=20`),
          ]);
          const chunkHtml = chunks.length ? chunks.map((item) => `
            <div class="subpanel">
              <strong>${escapeHtml(item.chunk_type)} | ${escapeHtml(item.section_path)}</strong>
              <div class="meta"><span class="mono">${escapeHtml(item.chunk_id)}</span><span>page=${escapeHtml(item.page_no ?? '-')}</span></div>
              <div>${escapeHtml(item.content)}</div>
            </div>
          `).join('') : '<div class="card">当前文档还没有 chunk。</div>';
          document.getElementById('documentPreview').innerHTML = `
            <div class="card">
              <strong>${escapeHtml(doc.file_name)}</strong>
              <div class="meta">
                <span class="mono">${escapeHtml(doc.document_id)}</span>
                <span>${escapeHtml(doc.doc_type)}</span>
                <span>${escapeHtml(doc.parse_status)}</span>
                <span>chunks=${escapeHtml(doc.chunk_count)}</span>
              </div>
              <div class="tiny">storage_path=${escapeHtml(doc.storage_path || '')}</div>
            </div>
            ${chunkHtml}
          `;
        } catch (error) {
          document.getElementById('documentPreview').innerHTML = `<div class="card">加载文档失败：${escapeHtml(error.message)}</div>`;
        }
      }

      async function loadTrace(traceId) {
        try {
          const trace = await fetchJson(`${apiPrefix}/audit/logs/${traceId}`);
          latestTraceId = traceId;
          const agents = (trace.agent_traces || []).map((item) => `
            <div class="subpanel">
              <strong>${escapeHtml(item.role)}</strong>
              <div>${escapeHtml(item.summary || '')}</div>
              <div class="tiny">${escapeHtml(JSON.stringify(item.details || {}, null, 2))}</div>
            </div>
          `).join('');
          const reasoning = (trace.reasoning_path || []).map((item) => `
            <div class="subpanel">
              <strong>Step ${escapeHtml(item.step || '')}</strong>
              <div class="meta"><span>${escapeHtml(item.source || '')}</span><span>${escapeHtml(item.evidence_id || '')}</span></div>
              <div>${escapeHtml(item.summary || '')}</div>
            </div>
          `).join('');
          document.getElementById('qaResult').innerHTML += `
            <div class="card">
              <strong>Trace 详情</strong>
              <div class="meta"><span class="mono">${escapeHtml(trace.trace_id)}</span><span>${escapeHtml(trace.route)}</span><span>${escapeHtml(trace.risk_level)}</span></div>
              <div class="answer">${escapeHtml(trace.final_answer || '')}</div>
            </div>
            <div class="card"><strong>Agent Traces</strong><div class="list">${agents || '暂无'}</div></div>
            <div class="card"><strong>Trace Reasoning</strong><div class="list">${reasoning || '暂无'}</div></div>
          `;
        } catch (error) {
          setStatus('qaStatus', `加载 Trace 失败：${error.message}`, true);
        }
      }

      function renderGraph(graph) {
        const entities = (graph.entities || []).slice(0, 10).map((item) => `
          <div class="subpanel">
            <strong>${escapeHtml(item.name || '')}</strong>
            <div class="meta"><span>${escapeHtml(item.type || '')}</span></div>
          </div>
        `).join('');
        const relations = (graph.relations || []).slice(0, 10).map((item) => `
          <div class="subpanel">
            <strong>${escapeHtml(item.source || '')}</strong>
            <div class="meta"><span>${escapeHtml(item.type || '')}</span><span>${escapeHtml(item.target || '')}</span></div>
          </div>
        `).join('');
        document.getElementById('graphSnapshot').innerHTML = `
          <div class="card">
            <strong>节点</strong>
            <div class="meta"><span>count=${escapeHtml(graph.counts?.entities ?? 0)}</span></div>
            <div class="list">${entities || '暂无节点'}</div>
          </div>
          <div class="card">
            <strong>边</strong>
            <div class="meta"><span>count=${escapeHtml(graph.counts?.relations ?? 0)}</span></div>
            <div class="list">${relations || '暂无关系'}</div>
          </div>
        `;
      }

      async function uploadAndIngest() {
        const file = document.getElementById('fileInput').files[0];
        if (!file) {
          setStatus('uploadStatus', '请先选择文件。', true);
          return;
        }
        try {
          setStatus('uploadStatus', '正在上传文件...');
          const formData = new FormData();
          formData.append('file', file);
          const upload = await fetchJson(`${apiPrefix}/documents/upload`, { method: 'POST', body: formData });
          setStatus('uploadStatus', `上传完成，document_id=${upload.document_id}，正在发起入库...`);
          const job = await fetchJson(`${apiPrefix}/ingestion/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_type: 'document', document_id: upload.document_id }),
          });
          setStatus('uploadStatus', `入库完成。job_id=${job.job.job_id}\nresult=${JSON.stringify(job.result, null, 2)}`);
          await refreshWorkspace();
          await loadDocumentPreview(upload.document_id);
        } catch (error) {
          setStatus('uploadStatus', `上传或入库失败：${error.message}`, true);
        }
      }

      async function askQuestion() {
        const question = document.getElementById('questionInput').value.trim();
        const userId = document.getElementById('userId').value.trim();
        const conversationId = document.getElementById('conversationId').value.trim();
        if (!question) {
          setStatus('qaStatus', '问题不能为空。', true);
          return;
        }
        try {
          setStatus('qaStatus', '正在检索和生成答案...');
          const response = await fetchJson(`${apiPrefix}/qa/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, user_id: userId, conversation_id: conversationId }),
          });
          latestTraceId = response.trace_id;
          setStatus('qaStatus', `问答完成，trace_id=${response.trace_id}`);
          renderQA(response);
          await refreshWorkspace();
          await loadTrace(response.trace_id);
        } catch (error) {
          setStatus('qaStatus', `问答失败：${error.message}`, true);
        }
      }

      function renderQA(payload) {
        const target = document.getElementById('qaResult');
        const evidenceHtml = (payload.evidence || []).map((item) => `
          <div class="evidence-item">
            <div><strong>${escapeHtml(item.source)}</strong> <span class="mono">${escapeHtml(item.evidence_id)}</span></div>
            <div class="meta"><span>score=${escapeHtml(item.score)}</span></div>
            <div>${escapeHtml(item.content)}</div>
          </div>
        `).join('');
        const reasoningHtml = (payload.reasoning_path || []).map((item) => `
          <div class="subpanel">
            <strong>Step ${escapeHtml(item.step || '')}</strong>
            <div class="meta"><span>${escapeHtml(item.source || '')}</span><span>${escapeHtml(item.evidence_id || '')}</span></div>
            <div>${escapeHtml(item.summary || '')}</div>
          </div>
        `).join('');
        target.innerHTML = `
          <div class="card">
            <strong>答案</strong>
            <div class="answer">${escapeHtml(payload.answer || '')}</div>
            <div class="meta">
              <span class="mono">${escapeHtml(payload.trace_id)}</span>
              <span>${escapeHtml(payload.retrieval_strategy)}</span>
              <span>${escapeHtml(payload.risk_level)}</span>
              <span>${escapeHtml(payload.fallback_mode)}</span>
            </div>
            <div class="actions"><button class="alt" onclick="loadTrace('${escapeHtml(payload.trace_id)}')">查看完整 Trace</button></div>
          </div>
          <div class="card">
            <strong>证据</strong>
            <div class="evidence">${evidenceHtml || '暂无证据'}</div>
          </div>
          <div class="card">
            <strong>推理路径</strong>
            <div class="list">${reasoningHtml || '暂无推理路径'}</div>
          </div>
        `;
      }

      refreshWorkspace().catch((error) => {
        setStatus('uploadStatus', `初始化失败：${error.message}`, true);
      });
    </script>
  </body>
</html>
"""


@router.get("/workspace", response_class=HTMLResponse, include_in_schema=False)
def workspace_page() -> HTMLResponse:
    return HTMLResponse(WORKSPACE_HTML)
