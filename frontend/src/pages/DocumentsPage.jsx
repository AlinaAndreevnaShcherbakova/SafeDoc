import React, { useEffect, useMemo, useState } from "react";
import Alert from "react-bootstrap/Alert";
import Badge from "react-bootstrap/Badge";
import Button from "react-bootstrap/Button";
import Card from "react-bootstrap/Card";
import Col from "react-bootstrap/Col";
import Form from "react-bootstrap/Form";
import InputGroup from "react-bootstrap/InputGroup";
import Modal from "react-bootstrap/Modal";
import Row from "react-bootstrap/Row";
import Stack from "react-bootstrap/Stack";
import Table from "react-bootstrap/Table";
import Tabs from "react-bootstrap/Tabs";
import Tab from "react-bootstrap/Tab";

import { api } from "../api/client";
import Loader from "../components/Loader";
import { useAuth } from "../context/AuthContext";

const VISIBILITY_OPTIONS = ["by_request", "read_all", "edit_all"];

export default function DocumentsPage() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState("mine");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [uploadFile, setUploadFile] = useState(null);
  const [uploadComment, setUploadComment] = useState("");
  const [uploadVisibility, setUploadVisibility] = useState("by_request");
  const [uploading, setUploading] = useState(false);

  const [linkExpiresAt, setLinkExpiresAt] = useState("");
  const [lastPublicLink, setLastPublicLink] = useState("");
  const [linksByDoc, setLinksByDoc] = useState({});

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTitle, setPreviewTitle] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");

  const [versionsOpen, setVersionsOpen] = useState(false);
  const [versionDocId, setVersionDocId] = useState(null);
  const [versions, setVersions] = useState([]);

  const sortedDocs = useMemo(() => [...documents].sort((a, b) => b.id - a.id), [documents]);
  const myDocs = useMemo(() => sortedDocs.filter((doc) => doc.owner_id === user?.id), [sortedDocs, user?.id]);
  const sharedDocs = useMemo(() => sortedDocs.filter((doc) => doc.owner_id !== user?.id), [sortedDocs, user?.id]);

  async function loadDocuments() {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/documents", { params: { search } });
      setDocuments(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось загрузить документы");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUpload(event) {
    event.preventDefault();
    if (!uploadFile) {
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("visibility", uploadVisibility);
      if (uploadComment) {
        formData.append("comment", uploadComment);
      }
      await api.post("/documents", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadFile(null);
      setUploadComment("");
      await loadDocuments();
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка загрузки файла");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    try {
      await api.delete(`/documents/${id}`);
      await loadDocuments();
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка удаления");
    }
  }

  function formatSize(sizeBytes) {
    if (!Number.isFinite(sizeBytes) || sizeBytes < 0) return "0 Б";
    const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
    if (sizeBytes < 1024) return `${sizeBytes} Б`;
    const exponent = Math.min(Math.floor(Math.log(sizeBytes) / Math.log(1024)), units.length - 1);
    const value = sizeBytes / 1024 ** exponent;
    const rounded = value >= 10 ? Math.round(value) : Math.round(value * 10) / 10;
    return `${rounded} ${units[exponent]}`;
  }

  async function handleDownload(id, name) {
    try {
      const response = await api.get(`/documents/${id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка скачивания");
    }
  }

  async function handleCreatePublicLink(id) {
    if (!linkExpiresAt) {
      setError("Укажите срок действия ссылки");
      return;
    }
    //проверка что введенная дата не позже нынешней
    const parsedDate = new Date(linkExpiresAt);
    if (Number.isNaN(parsedDate.getTime()) || parsedDate <= new Date()) {
      setError("Укажите корректные дату и время действия ссылки в будущем");
      return;
    }

    try {
      const { data } = await api.post(`/links/${id}`, {
        expires_at: parsedDate.toISOString(),
      });
      const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin;
      setLastPublicLink(`${baseUrl}/links/public/${data.token}`);
      await loadLinksForDocument(id);
    } catch (err) {
      setError(err?.response?.data?.detail || "Ошибка создания ссылки");
    }
  }

  async function loadLinksForDocument(docId) {
    try {
      const { data } = await api.get(`/links/${docId}`);
      setLinksByDoc((prev) => ({ ...prev, [docId]: data }));
    } catch {
      setLinksByDoc((prev) => ({ ...prev, [docId]: [] }));
    }
  }

  async function handleRevokeLink(linkId, docId) {
    try {
      await api.post(`/links/${linkId}/revoke`);
      await loadLinksForDocument(docId);
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось отозвать ссылку");
    }
  }

  async function handlePreview(doc) {
    try {
      const response = await api.get(`/documents/${doc.id}/preview`, { responseType: "blob" });
      const contentType = response.headers?.["content-type"] || doc.mime || "application/octet-stream";
      const blob = new Blob([response.data], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      setPreviewTitle(doc.name);
      setPreviewUrl(url);
      setPreviewOpen(true);
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось открыть предпросмотр");
    }
  }

  function closePreview() {
    setPreviewOpen(false);
    if (previewUrl) {
      window.URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl("");
    setPreviewTitle("");
  }

  async function openVersions(docId) {
    try {
      const { data } = await api.get(`/documents/${docId}/versions`);
      setVersionDocId(docId);
      setVersions(data);
      setVersionsOpen(true);
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось получить список версий");
    }
  }

  async function restoreVersion(version) {
    if (!versionDocId) return;
    try {
      await api.post(`/documents/${versionDocId}/restore/${version}`);
      await loadDocuments();
      await openVersions(versionDocId);
    } catch (err) {
      setError(err?.response?.data?.detail || "Не удалось восстановить версию");
    }
  }

  async function handleSearchSubmit(event) {
    event.preventDefault();
    await loadDocuments();
  }

  async function handleResetSearch() {
    setSearch("");
    setTimeout(() => {
      loadDocuments();
    }, 0);
  }

  function renderDocumentsTable(rows, emptyText) {
    if (rows.length === 0) {
      return <Alert variant="light" className="mb-0">{emptyText}</Alert>;
    }
    return (
      <Table responsive hover>
        <thead>
          <tr>
            <th>ID</th>
            <th>Имя</th>
            <th>Размер</th>
            <th>Видимость</th>
            <th>Доступные действия</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((doc) => (
            <tr key={doc.id}>
              <td>{doc.id}</td>
              <td>{doc.name}</td>
              <td>{formatSize(doc.size_bytes)}</td>
              <td>
                <Badge bg="secondary">{doc.visibility}</Badge>
              </td>
              <td>
                <Stack direction="horizontal" gap={2} className="flex-wrap">
                  <Button size="sm" variant="outline-info" onClick={() => handlePreview(doc)}>
                    Предпросмотр
                  </Button>
                  <Button size="sm" variant="outline-primary" onClick={() => handleDownload(doc.id, doc.name)}>
                    Скачать
                  </Button>
                  <Button size="sm" variant="outline-secondary" onClick={() => openVersions(doc.id)}>
                    Версии
                  </Button>
                  <Button size="sm" variant="outline-success" onClick={() => handleCreatePublicLink(doc.id)}>
                    Создать ссылку
                  </Button>
                  <Button size="sm" variant="outline-danger" onClick={() => handleDelete(doc.id)}>
                    Удалить
                  </Button>
                </Stack>
                <Stack direction="horizontal" gap={2} className="mt-2 flex-wrap">
                  <Button size="sm" variant="outline-dark" onClick={() => loadLinksForDocument(doc.id)}>
                    Показать ссылки
                  </Button>
                  {(linksByDoc[doc.id] || []).filter((link) => !link.revoked_at).map((link) => (
                    <Button
                      key={link.id}
                      size="sm"
                      variant="outline-warning"
                      onClick={() => handleRevokeLink(link.id, doc.id)}
                    >
                      Отозвать ссылку #{link.id}
                    </Button>
                  ))}
                </Stack>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  }

  return (
    <Stack gap={3}>
      <Card>
        <Card.Body>
          <Card.Title>Загрузка документа</Card.Title>
          <Form onSubmit={handleUpload}>
            <Row className="g-2">
              <Col md={4}>
                <Form.Control type="file" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} required />
              </Col>
              <Col md={3}>
                <Form.Select value={uploadVisibility} onChange={(e) => setUploadVisibility(e.target.value)}>
                  {VISIBILITY_OPTIONS.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </Form.Select>
              </Col>
              <Col md={3}>
                <Form.Control
                  placeholder="Комментарий"
                  value={uploadComment}
                  onChange={(e) => setUploadComment(e.target.value)}
                />
              </Col>
              <Col md={2}>
                <Button type="submit" className="w-100" disabled={uploading}>
                  {uploading ? "..." : "Загрузить"}
                </Button>
              </Col>
            </Row>
          </Form>
        </Card.Body>
      </Card>

      <Card>
        <Card.Body>
          <Card.Title>Документы</Card.Title>
          <Form onSubmit={handleSearchSubmit}>
            <InputGroup className="mb-3">
              <Form.Control
                placeholder="Введите название для поиска"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <Button variant="outline-secondary" type="submit">
                Найти
              </Button>
              <Button variant="outline-secondary" onClick={handleResetSearch}>
                Сбросить
              </Button>
            </InputGroup>
          </Form>

          <Row className="mb-3">
            <Col md={4}>
              <Form.Control
                type="datetime-local"
                value={linkExpiresAt}
                onChange={(e) => setLinkExpiresAt(e.target.value)}
              />
              <Form.Text>Укажите срок действия для новой публичной ссылки</Form.Text>
            </Col>
          </Row>

          {error && <Alert variant="danger">{error}</Alert>}
          {lastPublicLink && (
            <Alert variant="success" className="small">
              Публичная ссылка: <a href={lastPublicLink}>{lastPublicLink}</a>
            </Alert>
          )}

          {loading ? <Loader /> : (
            <Tabs activeKey={activeTab} onSelect={(tab) => setActiveTab(tab || "mine")}>
              <Tab eventKey="mine" title="Мои файлы">
                <div className="pt-3">{renderDocumentsTable(myDocs, "Вы не загрузили ни одного файла")}</div>
              </Tab>
              <Tab eventKey="shared" title="Доступные мне">
                <div className="pt-3">{renderDocumentsTable(sharedDocs, "Вам пока не предоставлен доступ ни к одному файлу")}</div>
              </Tab>
            </Tabs>
          )}
        </Card.Body>
      </Card>

      <Modal show={previewOpen} onHide={closePreview} size="xl">
        <Modal.Header closeButton>
          <Modal.Title>Предпросмотр: {previewTitle}</Modal.Title>
        </Modal.Header>
        <Modal.Body style={{ minHeight: "70vh" }}>
          {previewUrl ? (
            <iframe title="preview" src={previewUrl} style={{ width: "100%", height: "65vh", border: 0 }} />
          ) : (
            <Alert variant="light">Предпросмотр недоступен.</Alert>
          )}
        </Modal.Body>
      </Modal>

      <Modal show={versionsOpen} onHide={() => setVersionsOpen(false)}>
        <Modal.Header closeButton>
          <Modal.Title>История версий</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {versions.length === 0 ? (
            <Alert variant="light" className="mb-0">У выбранного файла только одна версия</Alert>
          ) : (
            <Table responsive hover>
              <thead>
                <tr>
                  <th>Версия</th>
                  <th>Автор</th>
                  <th>Дата</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {versions.map((row) => (
                  <tr key={row.id}>
                    <td>{row.version}</td>
                    <td>{row.author_id}</td>
                    <td>{new Date(row.created_at).toLocaleString("ru-RU")}</td>
                    <td>
                      <Button size="sm" variant="outline-primary" onClick={() => restoreVersion(row.version)}>
                        Восстановить
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Modal.Body>
      </Modal>
    </Stack>
  );
}
