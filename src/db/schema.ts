import { relations } from 'drizzle-orm';
import { boolean, integer, pgTable, serial, text, timestamp } from 'drizzle-orm/pg-core';

// Users table (Firebase Auth linkage)
export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  uid: text('uid').notNull().unique(),
  email: text('email').notNull(),
  createdAt: timestamp('created_at').defaultNow(),
});

// Projects table
export const projects = pgTable('projects', {
  id: text('id').primaryKey(),
  userId: integer('user_id').references(() => users.id),
  name: text('name').notNull(),
  description: text('description').notNull(),
  requirements: text('requirements').notNull(), // JSON stringified array of requirements
  status: text('status').notNull().default('created'),
  type: text('type').default('web'),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Runs table
export const runs = pgTable('runs', {
  id: serial('id').primaryKey(),
  projectId: text('project_id')
    .references(() => projects.id)
    .notNull(),
  stage: text('stage').notNull().default('architect'),
  status: text('status').notNull().default('queued'),
  attempts: integer('attempts').notNull().default(1),
  error: text('error'),
  cancelRequested: boolean('cancel_requested').notNull().default(false),
  publish: boolean('publish').notNull().default(false),
  deploy: boolean('deploy').notNull().default(false),
  startedAt: timestamp('started_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Build & Agent execution events
export const events = pgTable('events', {
  id: serial('id').primaryKey(),
  projectId: text('project_id')
    .references(() => projects.id)
    .notNull(),
  runId: integer('run_id').references(() => runs.id),
  type: text('type').notNull().default('log'),
  stage: text('stage').notNull().default('architect'),
  status: text('status').notNull().default('running'),
  message: text('message'),
  metadata: text('metadata'), // JSON stringified metadata
  createdAt: timestamp('created_at').defaultNow(),
});

// Generated project workspace files
export const projectFiles = pgTable('project_files', {
  id: serial('id').primaryKey(),
  projectId: text('project_id')
    .references(() => projects.id)
    .notNull(),
  path: text('path').notNull(),
  content: text('content').notNull(),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Quality gate & test execution reports
export const testReports = pgTable('test_reports', {
  id: serial('id').primaryKey(),
  projectId: text('project_id')
    .references(() => projects.id)
    .notNull(),
  runId: integer('run_id').references(() => runs.id),
  testsJson: text('tests_json').notNull().default('[]'),
  testerFindings: text('tester_findings').notNull().default('[]'),
  reviewerFindings: text('reviewer_findings').notNull().default('[]'),
  repairsJson: text('repairs_json').notNull().default('[]'),
  createdAt: timestamp('created_at').defaultNow(),
});

// Relations
export const usersRelations = relations(users, ({ many }) => ({
  projects: many(projects),
}));

export const projectsRelations = relations(projects, ({ one, many }) => ({
  author: one(users, {
    fields: [projects.userId],
    references: [users.id],
  }),
  runs: many(runs),
  events: many(events),
  files: many(projectFiles),
  testReports: many(testReports),
}));

export const runsRelations = relations(runs, ({ one, many }) => ({
  project: one(projects, {
    fields: [runs.projectId],
    references: [projects.id],
  }),
  events: many(events),
  testReports: many(testReports),
}));
