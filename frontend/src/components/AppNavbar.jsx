import React from "react";
import Button from "react-bootstrap/Button";
import Container from "react-bootstrap/Container";
import Nav from "react-bootstrap/Nav";
import Navbar from "react-bootstrap/Navbar";
import { NavLink } from "react-router-dom";

export default function AppNavbar({ isSuperadmin, onLogout }) {
  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="mb-4">
      <Container>
        <Navbar.Brand>SafeDoc</Navbar.Brand>
        <Navbar.Toggle aria-controls="main-nav" />
        <Navbar.Collapse id="main-nav">
          <Nav className="me-auto">
            <Nav.Link as={NavLink} to="/documents">
              Документы
            </Nav.Link>
            <Nav.Link as={NavLink} to="/requests">
              Заявки
            </Nav.Link>
            {isSuperadmin && (
              <Nav.Link as={NavLink} to="/users">
                Пользователи
              </Nav.Link>
            )}
          </Nav>
          <Button size="sm" variant="outline-light" onClick={onLogout}>
            Выйти
          </Button>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}
