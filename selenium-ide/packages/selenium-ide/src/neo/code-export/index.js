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

import UiState from '../stores/view/UiState'
import ModalState from '../stores/view/ModalState'
import exporter from 'code-export'
import { downloadUniqueFile } from '../IO/filesystem'
import { normalizeTestsInSuite } from '../IO/normalize'
import PluginManager from '../../plugin/manager'
import { availableLanguages as languages } from 'code-export'
import { userAgent } from '@seleniumhq/side-utils'
const vendorLanguages = PluginManager.plugins.vendorLanguages

export function availableLanguages() {
  return Object.keys(vendorLanguages).length
    ? { ...languages, ...vendorLanguages }
    : languages
}

export async function exportCodeToFile(
  selectedLanguages,
  { test, suite },
  { enableOriginTracing, beforeEachOptions }
) {
  const project = UiState.project.toJS()
  const { url, tests } = project
  for (const language of selectedLanguages) {
    let emittedCode
    let options = {
      url,
      tests,
      project,
      enableOriginTracing,
      beforeEachOptions: {
        browserName: userAgent.browserName,
        ...beforeEachOptions,
      },
    }
    console.log('exportCodeToFile', project, tests, url);
    options.test = test ? test : undefined
    options.suite = suite ? normalizeTestsInSuite({ suite, tests }) : undefined
    if (vendorLanguages.hasOwnProperty(language)) {
      const result = await PluginManager.emitMessage({
        action: 'export',
        entity: 'vendor',
        language,
        options,
      })
      emittedCode = result[0].response
    } else if (test) {
      emittedCode = await exporter.emit.test(language, options)
    } else if (suite) {
      emittedCode = await exporter.emit.suite(language, options)
    }
    console.log('emittedCode', emittedCode);
    if (emittedCode) {
      console.log('emittedCode.body7', emittedCode.body);
      return fetch('http://165.227.12.163:5000/actions', {
        body: JSON.stringify({
          name: randomString(),
          content: emittedCode.body,
        }),
        method: 'POST',
      }).then(response => {
        return response.json().then(json => {
           console.log('json', json);
           return `http://165.227.12.163:5000/invokations/${json.id}`
        });
      });
    }
  }
  ModalState.cancelCodeExport();
}

function randomString() {
   return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}
