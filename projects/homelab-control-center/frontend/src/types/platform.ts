export interface PlatformState {
  platform: string;

  git: {
    branch: string;
    commit: string;
  };

  containers: {
    running: number;
    unhealthy: number;
  };

  health: {
    status: string;
  };

  backup: {
    latest: string;
  };
}
