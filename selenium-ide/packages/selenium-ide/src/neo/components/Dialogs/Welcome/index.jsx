// Licensed to the Software Freedom Conservancy (SFC) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The SFC licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

import React from 'react'
import PropTypes from 'prop-types'
import { loadProject } from '../../../IO/filesystem'
import { observer } from 'mobx-react'
import UiState from '../../../stores/view/UiState'
import project from '../../../../../package.json'
import Modal from '../../Modal'
import DialogContainer from '../Dialog'
import logoFile from '../../../assets/images/selenium_blue_white32@3x.svg'
import { OpenInput } from '../../ActionButtons/Open'
import './style.css'

@observer
export default class WelcomeDialog extends React.Component {
  render() {
    return (
      <Modal className="stripped" isOpen={!this.props.isWelcomed}>
        <WelcomeDialogContents {...this.props} />
      </Modal>
    )
  }
  static propTypes = {
    isWelcomed: PropTypes.bool.isRequired,
  }
}

class WelcomeDialogContents extends React.Component {
  constructor(props) {
    super(props)
    this.startRecordingInNewProject = this.startRecordingInNewProject.bind(this)
    this.createNewProject = this.createNewProject.bind(this)
    this.openProject = this.openProject.bind(this)
    this.dismiss = this.dismiss.bind(this)
  }

  async startRecordingInNewProject() {
    this.props.hideWelcome()
    await this.props.createNewProject()
    this.props.completeWelcome()
    UiState.toggleRecord(false)
  }

  async createNewProject() {
    this.props.hideWelcome()
    await this.props.createNewProject()
    this.props.completeWelcome()
  }

  openProject(file) {
    loadProject(this.props.project, file)
    this.props.completeWelcome()
  }

  dismiss() {
    window.close()
  }

  render() {
    return (
      <DialogContainer
        className="welcome-dialog"
        title="Project base URL is missing or invalid!"
        type="info"
        renderImage={() => <img height={36} alt="se-ide-logo" src={logoFile} />}
        renderTitle={() => (
          <div>
            <div className="welcome-dialog__title">
              Welcome to Instant API!
            </div>
            <div className="welcome-dialog__subtitle">
              Version 0.0.0
            </div>
          </div>
        )}
        renderFooter={() => (
          <p>
          Make APIs easyagain!
          </p>
        )}
      >
        <div>
          <div>What would you like to do?</div>
          <ul className="welcome-dialog__options">
            <li>
              <a onClick={this.startRecordingInNewProject}>
                Create a new API
              </a>
            </li>
            <li className="file-open">
              <OpenInput
                onFileSelected={this.openProject}
                labelMarkup={<div>Open an existing API</div>}
              />
            </li>
          </ul>
        </div>
      </DialogContainer>
    )
  }
  static propTypes = {
    project: PropTypes.object.isRequired,
    createNewProject: PropTypes.func.isRequired,
    hideWelcome: PropTypes.func.isRequired,
    completeWelcome: PropTypes.func.isRequired,
  }
}
